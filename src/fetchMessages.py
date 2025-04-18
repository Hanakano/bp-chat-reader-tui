# src/fetchMessages.py
import json
import urllib.request
import os
from urllib.error import HTTPError
from tqdm import tqdm

def fetch_conversations(max_to_save=100):
    """Fetch conversations from Botpress API"""
    workspace_id = os.environ.get("BOTPRESS_WORKSPACE_ID")
    bot_id = os.environ.get("BOTPRESS_BOT_ID")
    token = os.environ.get("BOTPRESS_TOKEN")
    
    if not all([workspace_id, bot_id, token]):
        raise ValueError("Missing environment variables. Please set BOTPRESS_WORKSPACE_ID, BOTPRESS_BOT_ID, and BOTPRESS_TOKEN")
    
    base_url = "https://api.botpress.cloud/v1/chat/conversations"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-bot-id": bot_id,
        "x-workspace-id": workspace_id
    }
    
    conversation_ids = []
    next_token = None
    page = 1
    
    print(f"Fetching conversations (will save up to {max_to_save} with incoming messages)...")
    
    # We'll keep fetching until we either run out of conversations or have enough with incoming messages
    saved_count = 0
    progress_bar = tqdm(total=max_to_save, desc="Finding conversations with incoming messages")
    
    while saved_count < max_to_save:
        url = base_url + "?sortField=updatedAt&sortDirection=desc"
        if next_token:
            url += f"&nextToken={next_token}"
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
                # Extract conversation IDs from this page
                page_conversation_ids = [conv["id"] for conv in data.get("conversations", [])]
                
                if not page_conversation_ids:
                    print(f"\nNo more conversations available at page {page}")
                    break
                
                # Check each conversation for incoming messages
                for conv_id in page_conversation_ids:
                    messages = fetch_messages(conv_id)
                    has_incoming = any(msg.get("direction") == "incoming" for msg in messages)
                    
                    if has_incoming:
                        conversation_ids.append((conv_id, messages))
                        saved_count += 1
                        progress_bar.update(1)
                        
                        # Check if we've reached our limit
                        if saved_count >= max_to_save:
                            break
                
                # Check if there are more pages
                next_token = data.get("nextToken")
                if not next_token:
                    print(f"\nNo more pages available after page {page}")
                    break
                
                page += 1
                
        except HTTPError as e:
            print(f"\nError fetching conversations: {e}")
            break
    
    progress_bar.close()
    print(f"Found {saved_count} conversations with incoming messages")
    
    return conversation_ids

def fetch_messages(conversation_id):
    """Fetch messages for a specific conversation"""
    workspace_id = os.environ.get("BOTPRESS_WORKSPACE_ID")
    bot_id = os.environ.get("BOTPRESS_BOT_ID")
    token = os.environ.get("BOTPRESS_TOKEN")
    
    url = f"https://api.botpress.cloud/v1/chat/messages?conversationId={conversation_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-bot-id": bot_id,
        "x-workspace-id": workspace_id
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            # Sort messages by timestamp and extract relevant fields
            messages = data.get("messages", [])
            messages.sort(key=lambda m: m.get("updatedAt", ""))
            
            processed_messages = []
            for message in messages:
                msg_data = {
                    "type": message.get("type"),
                    "direction": message.get("direction"),
                    "timestamp": message.get("updatedAt")
                }
                
                # Extract text for text messages
                if message.get("type") == "text" and "payload" in message and "text" in message["payload"]:
                    msg_data["text"] = message["payload"]["text"]
                else:
                    msg_data["text"] = f"[{message.get('type', 'unknown')} message]"
                
                processed_messages.append(msg_data)
            
            return processed_messages
            
    except HTTPError as e:
        print(f"Error fetching messages for conversation {conversation_id}: {e}")
        return []

def save_conversations_to_jsonl(output_file="conversation_transcripts.jsonl", max_to_save=100):
    """Fetch conversations and save them to a JSONL file"""
    conversation_data = fetch_conversations(max_to_save)
    
    print(f"Saving {len(conversation_data)} conversations to {output_file}...")
    with open(output_file, "w") as f:
        for idx, (conversation_id, messages) in enumerate(conversation_data):
            conversation_data = {
                "conversation_id": conversation_id,
                "messages": messages
            }
            
            f.write(json.dumps(conversation_data) + "\n")
    
    print(f"Successfully saved {len(conversation_data)} conversations to {output_file}")
    return output_file

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch Botpress conversations and save them as JSONL")
    parser.add_argument("--output", "-o", default="conversation_transcripts.jsonl", help="Output JSONL file")
    parser.add_argument("--limit", "-l", type=int, default=40, help="Maximum number of conversations with incoming messages to save")
    
    args = parser.parse_args()
    
    save_conversations_to_jsonl(args.output, args.limit)
