# src/fetchMessages.py
"""
Fetches conversation transcripts from the Botpress Cloud API.

This script connects to the Botpress API, retrieves conversations, 
filters them to include only those with at least one 'incoming' message,
and saves the filtered conversations incrementally to a JSON Lines (.jsonl) file.
It processes message fetching concurrently to speed up the process.

Requires the following environment variables to be set:
- BOTPRESS_WORKSPACE_ID: Your Botpress workspace ID.
- BOTPRESS_BOT_ID: The ID of the bot whose conversations you want to fetch.
- BOTPRESS_TOKEN: A valid Botpress API token with necessary permissions.
"""

import json
import urllib.request
import os
import time
import datetime
import concurrent.futures
import sys
from urllib.error import HTTPError
from tqdm import tqdm
from typing import List, Dict, Tuple, Any, Optional, TextIO, TypeVarTuple # Added for type hints

# --- Constants ---
# Maximum number of concurrent API calls for fetching messages (can be overridden by args)
MAX_CONCURRENT_CALLS: int = 10

# --- Functions ---

def fetch_messages(conversation_id: str, createdAt: str, updatedAt: str) -> Dict[str, Any]:
    """
    Fetches and processes messages for a specific conversation ID from the Botpress API.

    Sorts messages by timestamp and extracts relevant fields ('type', 'direction', 
    'timestamp', 'text'). Determines if the conversation contains any incoming messages.

    Args:
        conversation_id: The unique identifier for the conversation.
        createdAt: When the chat started, passed through for metadata
        updatedAt: When the chat ended, passed through for metadata

    Returns:
        A dictionary containing:
        - 'conversation_id': The ID of the conversation processed.
        - 'messages': A list of processed message dictionaries, sorted by timestamp.
                      Each message dict contains 'type', 'direction', 'timestamp', 'text'.
        - 'has_incoming': A boolean indicating if any message in the conversation 
                          has direction 'incoming'.
        - 'error': None if successful, or a string describing the error if one occurred 
                   during fetching or processing.
    """
    workspace_id: Optional[str] = os.environ.get("BOTPRESS_WORKSPACE_ID")
    bot_id: Optional[str] = os.environ.get("BOTPRESS_BOT_ID")
    token: Optional[str] = os.environ.get("BOTPRESS_TOKEN")
    
    # Basic check within function - primary check is done at script start
    if not all([workspace_id, bot_id, token]):
        return {
            "conversation_id": conversation_id,
            "messages": [],
            "has_incoming": False,
            "error": "Missing environment variables (checked within fetch_messages)"
        }

    base_url: str = f"https://api.botpress.cloud/v1/chat/messages?conversationId={conversation_id}"
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "x-bot-id": bot_id or "",
        "x-workspace-id": workspace_id or ""
    }
    
    processed_messages: List[Dict[str, Any]] = []
    next_token = None
    page_count = 0
    
    # Continue fetching while we have a next token or it's the first request
    while next_token is not None or page_count == 0:
        try:
            url = base_url
            if next_token:
                url += f"&nextToken={next_token}"
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data: Dict[str, Any] = json.loads(response.read().decode('utf-8'))
                
                # Process this page of messages
                page_messages: List[Dict[str, Any]] = []
                raw_messages: List[Dict[str, Any]] = data.get("messages", [])
                
                for message in raw_messages:
                    msg_data: Dict[str, Any] = {
                        "type": message.get("type"),
                        "direction": message.get("direction"),
                        "timestamp": message.get("updatedAt")
                    }
                    
                    # Extract text for text messages
                    payload: Optional[Dict[str, Any]] = message.get("payload")
                    if message.get("type") == "text" and payload and "text" in payload:
                        msg_data["text"] = payload["text"]
                    else:
                        # Provide a more descriptive placeholder if text is missing
                        msg_type: str = message.get('type', 'unknown')
                        msg_data["text"] = f"[{msg_type} message]"
                    
                    page_messages.append(msg_data)
                
                # Get next token for pagination (if available)
                next_token = data.get("meta",{}).get("nextToken")
                               
                # Add messages from this page - newer messages come in later pages
                # so we append to the end for chronological order (oldest first)
                processed_messages.extend(page_messages)
                page_count += 1
                
        except HTTPError as e:
            error_message = f"HTTPError: {e.code} {e.reason}"
            try:
                # Try to read error details from response body if available
                error_body = e.read().decode('utf-8', errors='ignore')
                error_message += f" - Body: {error_body[:200]}"  # Limit body length
            except Exception:
                pass  # Ignore if reading body fails
            return {
                "conversation_id": conversation_id,
                "createdAt": createdAt,
                "updatedAt":updatedAt,
                "messages": [],
                "has_incoming": False,
                "error": error_message
            }
        except Exception as e:
            return {
                "conversation_id": conversation_id,
                "createdAt": createdAt,
                "updatedAt":updatedAt,
                "messages": [],
                "has_incoming": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    # Sort by timestamp as a final precaution
    processed_messages.sort(key=lambda m: m.get("timestamp", "") or "")
    
    # Check if this conversation has any incoming messages
    has_incoming: bool = any(msg.get("direction") == "incoming" for msg in processed_messages)
    
    return {
        "conversation_id": conversation_id,
        "createdAt": createdAt,
        "updatedAt":updatedAt,
        "messages": processed_messages,
        "has_incoming": has_incoming,
        "error": None  # Explicitly add error field for consistency
    }

def fetch_conversations_and_write(output_file_handle: TextIO, max_to_save: int = 100) -> int:
    """
    Fetches conversations from Botpress API, processes them in parallel,
    and writes valid ones (those with incoming messages) directly and 
    incrementally to the provided output file handle.

    Args:
        output_file_handle: An open text file handle in write or append mode 
                            where JSONL data will be written.
        max_to_save: The maximum number of conversations with incoming messages
                     to fetch and save. Defaults to 100.

    Returns:
        The total number of conversations successfully saved to the file.
        
    Raises:
        ValueError: If required environment variables are not set.
    """
    workspace_id: Optional[str] = os.environ.get("BOTPRESS_WORKSPACE_ID")
    bot_id: Optional[str] = os.environ.get("BOTPRESS_BOT_ID")
    token: Optional[str] = os.environ.get("BOTPRESS_TOKEN")
    
    if not all([workspace_id, bot_id, token]):
        # This check is redundant if called after the main block check,
        # but good practice for function independence.
        raise ValueError("Missing environment variables. Please set BOTPRESS_WORKSPACE_ID, BOTPRESS_BOT_ID, and BOTPRESS_TOKEN")
    
    base_url: str = "https://api.botpress.cloud/v1/chat/conversations"
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "x-bot-id": bot_id or "",
        "x-workspace-id": workspace_id or ""
    }
    
    saved_count: int = 0
    page: int = 1
    next_token: Optional[str] = None
    processed_ids_count: int = 0 # Track total conversations IDs processed
    
    # Create progress bar for saving valid conversations
    progress_bar = tqdm(total=max_to_save, desc="Saving valid conversations", unit="conv", leave=True)
    
    try:
        while saved_count < max_to_save:
            # 1. Get a batch of conversation IDs
            # Fetch larger batches (e.g., 100) to reduce list API calls
            current_url = base_url + "?sortField=updatedAt&sortDirection=desc&limit=100" 
            if next_token:
                current_url += f"&nextToken={next_token}"
            
            try:
                req = urllib.request.Request(current_url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    list_data: Dict[str, Any] = json.loads(response.read().decode('utf-8'))
                    
                    # Extract conversation IDs from this page
                    page_conversation_data: List[Tuple[str,str, str]] = [
                        (conv["id"], conv["createdAt"], conv["updatedAt"]) for conv in list_data.get("conversations", []) if "id" in conv
                    ]
                    
                    if not page_conversation_data:
                        tqdm.write(f"\nNo more conversations available at page {page}.")
                        break
                    
                    current_batch_size = len(page_conversation_data)
                    processed_ids_count += current_batch_size
                    tqdm.write(f"Fetched page {page}, {current_batch_size} conversation IDs. Total processed: {processed_ids_count} Total saved: {saved_count}")
                    
                    # 2. Process conversations in parallel
                    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CALLS) as executor:
                        # Map Future object back to conversation ID
                        future_to_id: Dict[concurrent.futures.Future, str] = {
                            executor.submit(fetch_messages, conv_id, createdAt, updatedAt): conv_id 
                            for conv_id, createdAt, updatedAt in page_conversation_data
                        }
                        
                        # Process results as they complete
                        for future in concurrent.futures.as_completed(future_to_id):
                            conv_id = future_to_id[future]
                            try:
                                result: Dict[str, Any] = future.result()
                                
                                if result["error"]:
                                     tqdm.write(f"Skipping conv {conv_id} due to error: {result['error']}")
                                     continue # Skip conversations with errors

                                if result["has_incoming"]:
                                    # Prepare data for JSON line
                                    # Convert ISO timestamps to datetime objects and calculate duration in minutes
                                    created_datetime = datetime.datetime.fromisoformat(result["createdAt"].replace("Z", "+00:00"))
                                    updated_datetime = datetime.datetime.fromisoformat(result["updatedAt"].replace("Z", "+00:00"))
                                    duration_minutes = (updated_datetime - created_datetime).total_seconds() / 60.0
                                    output_data: Dict[str, Any] = {
                                        "conversation_id": result["conversation_id"],
                                        "messages": result["messages"],
                                        "metadata":{
                                            "createdDate":result["createdAt"],
                                            "duration":duration_minutes,
                                            "tags":["unread"]
                                        }
                                    }
                                    # Write immediately to the file
                                    output_file_handle.write(json.dumps(output_data) + "\n")
                                    # Flush to ensure it's written to disk, critical for resilience
                                    output_file_handle.flush() 

                                    saved_count += 1
                                    progress_bar.update(1)
                                    
                                    # Check if we've reached our limit
                                    if saved_count >= max_to_save:
                                        tqdm.write(f"\nTarget of {max_to_save} conversations reached.")
                                        # Attempt to cancel remaining futures to stop unnecessary API calls
                                        # Note: Cancellation is best-effort and might not stop tasks already running.
                                        for remaining_future in future_to_id:
                                            remaining_future.cancel()
                                        # Shutdown quickly without waiting for cancelled futures
                                        executor.shutdown(wait=False) 
                                        # Python 3.9+ can use: executor.shutdown(wait=False, cancel_futures=True)
                                        break # Exit the inner as_completed loop

                            except concurrent.futures.CancelledError:
                                tqdm.write(f"Task for conv {conv_id} was cancelled.")
                            except Exception as exc:
                                # Catch potential errors during future.result() itself or processing
                                tqdm.write(f"\nError processing result for conversation {conv_id}: {exc}")
                        
                    # Check if we've reached our limit after processing the batch
                    if saved_count >= max_to_save:
                        break # Exit the outer while loop
                        
                    # Check if there are more pages available (look inside 'meta' object)
                    next_token = list_data.get("meta", {}).get("nextToken")
                    if not next_token:
                        tqdm.write(f"\nNo more pages available after page {page} (nextToken not found).")
                        break
                    
                    page += 1
                    # Optional: Add a small delay between pages if hitting rate limits frequently
                    # time.sleep(0.5) 
                    
            except HTTPError as e:
                tqdm.write(f"\nError fetching conversations list (page {page}): {e}")
                if e.code == 429: # Too Many Requests
                    wait_time = 60
                    tqdm.write(f"Rate limit likely hit. Waiting {wait_time} seconds before retrying page {page}...")
                    time.sleep(wait_time)
                    # Don't increment page, retry the same page
                    continue 
                else:
                    tqdm.write("Aborting due to unrecoverable HTTP error.")
                    break # Break on other HTTP errors
            except Exception as e:
                tqdm.write(f"\nUnexpected error fetching conversations list (page {page}): {e}")
                import traceback
                traceback.print_exc() # Print stack trace for unexpected errors
                break
    
    finally:
        # Ensure progress bar is closed properly
        progress_bar.close()
        tqdm.write(f"\nFinished fetching process. Saved {saved_count} conversations.")
    
    return saved_count

def save_conversations_to_jsonl(output_file: str = "conversation_transcripts.jsonl", max_to_save: int = 100) -> int:
    """
    Opens the output file and orchestrates fetching and writing conversations.

    This function handles opening and closing the output file and calls 
    `fetch_conversations_and_write` to perform the main work.

    Args:
        output_file: The path to the JSONL file to be created or overwritten.
                     Defaults to "conversation_transcripts.jsonl".
        max_to_save: The maximum number of conversations with incoming messages
                     to fetch and save. Defaults to 100.

    Returns:
        The total number of conversations actually saved to the file.
    """
    print(f"Attempting to save up to {max_to_save} conversations to '{output_file}'...")
    saved_count: int = 0
    try:
        # Open the file in write mode ('w') with UTF-8 encoding. 
        # This will overwrite the file if it exists. Use 'a' to append.
        with open(output_file, "w", encoding='utf-8') as f:
            saved_count = fetch_conversations_and_write(f, max_to_save)
    except IOError as e:
        print(f"\nError opening or writing to file '{output_file}': {e}", file=sys.stderr)
    except ValueError as e: # Catch ValueError from env var check
         print(f"\nError: {e}", file=sys.stderr)
    except Exception as e:
        # Catch any other unexpected errors during file handling or the main process
        print(f"\nAn unexpected error occurred during the process: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc() # Print stack trace for unexpected errors
    finally:
        # This message will print regardless of success or failure
        print(f"Process completed. Saved a total of {saved_count} conversations to '{output_file}'.")
    
    return saved_count


# --- Main Execution ---
if __name__ == "__main__":
    # --- Argument Parsing ---
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fetch Botpress conversations with incoming messages and save incrementally as JSONL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help message
        )
    parser.add_argument(
        "--output", "-o", 
        default="conversation_transcripts.jsonl", 
        help="Output JSONL file path."
        )
    parser.add_argument(
        "--limit", "-l", 
        type=int, 
        default=40, 
        help="Maximum number of conversations (with incoming messages) to save."
        )
    parser.add_argument(
        "--concurrent", "-c", 
        type=int, 
        default=10, 
        help="Maximum number of concurrent API calls for fetching messages."
        )
    
    args = parser.parse_args()
    
    # --- Set Global Concurrency Limit ---
    # Validate concurrency limit to be positive
    if args.concurrent > 0:
        MAX_CONCURRENT_CALLS = args.concurrent
    else:
        print("Warning: Concurrent calls must be positive. Using default value of 10.", file=sys.stderr)
        MAX_CONCURRENT_CALLS = 10 # Reset to default if invalid

    # --- Environment Variable Check ---
    # Perform the critical environment variable check early
    required_env_vars = ["BOTPRESS_WORKSPACE_ID", "BOTPRESS_BOT_ID", "BOTPRESS_TOKEN"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set these variables before running the script.", file=sys.stderr)
        sys.exit(1) # Exit if required variables are missing

    # --- Run the main process ---
    print(f"Starting conversation fetch process...")
    print(f" - Output file: {args.output}")
    print(f" - Saving limit: {args.limit}")
    print(f" - Max concurrent message fetches: {MAX_CONCURRENT_CALLS}")
    
    start_time = time.time()
    actual_saved_count = save_conversations_to_jsonl(args.output, args.limit)
    end_time = time.time()
    
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds.")
    
    # Optional: Indicate success or if limit wasn't reached
    if actual_saved_count == args.limit:
        print("Reached the specified limit.")
    elif actual_saved_count < args.limit:
        print(f"Found and saved {actual_saved_count} conversations, which is less than the limit of {args.limit}.")
