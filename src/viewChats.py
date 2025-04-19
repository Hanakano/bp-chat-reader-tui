# src/viewChats.py
"""
TUI Viewer for Botpress Conversation Transcripts in JSONL format.

Main entry point for the conversation viewer application.
"""
import json
import os
import curses
import argparse
from typing import List, Dict, Any

# Import modules for different functionality
from viewer.displayConversation import display_conversation
from viewer.searchConversation import search_conversation
from viewer.filterConversation import filter_by_tags
from viewer.tagConversation import manage_tags
from viewer.helpWindow import show_help

class ConversationData:
    """Class to handle loading and managing conversation data"""
    def __init__(self, filename: str):
        self.filename = filename
        self.conversations: List[Dict[str, Any]] = []
        self.current_index = 0
        self.scroll_position = 0
        self.load_conversations()
        
    def load_conversations(self) -> None:
        """Load conversations from the JSONL file"""
        if not os.path.exists(self.filename):
            raise FileNotFoundError(f"File not found: {self.filename}")
        
        with open(self.filename, 'r') as f:
            for line in f:
                try:
                    conversation = json.loads(line.strip())
                    if conversation.get("messages"):
                        self.conversations.append(conversation)
                except json.JSONDecodeError:
                    continue
        
        if not self.conversations:
            raise ValueError("No conversations found in the file")
    
    def toggle_read(self) -> None:
        """Mark current conversation as read or unread"""
        if not self.conversations:
            return
            
        # Get current conversation
        conversation = self.conversations[self.current_index]
        
        # Check if metadata and tags exist
        if "metadata" not in conversation:
            conversation["metadata"] = {}
        if "tags" not in conversation["metadata"]:
            conversation["metadata"]["tags"] = []
            
        # Remove "unread" tag if present
        if "unread" in conversation["metadata"]["tags"]:
            conversation["metadata"]["tags"].append("read")
            conversation["metadata"]["tags"].remove("unread")
        # Add read tag if it's not present already
        elif "read" in conversation["metadata"]["tags"]:
            conversation["metadata"]["tags"].append("unread")
            conversation["metadata"]["tags"].remove("read")

        # Save changes to file
        self._save_conversations()
            
    def add_tag(self, tag: str) -> None:
        """Add a tag to the current conversation"""
        if not self.conversations or not tag:
            print(f"Warning: Need both tag and conversations to add tag. Tag: {tag} Conversations {self.conversations}")
            return
            
        # Get current conversation
        conversation = self.conversations[self.current_index]
        
        # Check if metadata and tags exist
        if "metadata" not in conversation:
            conversation["metadata"] = {}
        if "tags" not in conversation["metadata"]:
            conversation["metadata"]["tags"] = []
            
        # Add tag if not already present
        if tag not in conversation["metadata"]["tags"]:
            conversation["metadata"]["tags"].append(tag)
            
        # Save changes to file
        self._save_conversations()
        print(self.conversations[self.current_index]['metadata'])
            
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the current conversation"""
        if not self.conversations or not tag:
            return
            
        # Get current conversation
        conversation = self.conversations[self.current_index]
        
        # Check if metadata and tags exist
        if "metadata" not in conversation or "tags" not in conversation["metadata"]:
            return
            
        # Remove tag if present
        if tag in conversation["metadata"]["tags"]:
            conversation["metadata"]["tags"].remove(tag)
            
        # Save changes to file
        self._save_conversations()
    
    def get_all_tags(self) -> List[str]:
        """Get a list of all unique tags across all conversations"""
        all_tags = set()
        
        for conv in self.conversations:
            if "metadata" in conv and "tags" in conv["metadata"]:
                all_tags.update(conv["metadata"]["tags"])
                
        return sorted(list(all_tags))
    
    def _save_conversations(self) -> None:
        """Save conversations back to the JSONL file"""
        try:
            with open(self.filename, 'w') as f:
                for conv in self.conversations:
                    f.write(json.dumps(conv) + "\n")
        except Exception as e:
            # This is a simple implementation - in production code,
            # we'd want more robust error handling and possibly a backup
            print(f"Error saving conversations: {e}")

def run_viewer(stdscr, data: ConversationData) -> None:
    """Main function to run the TUI viewer"""
    curses.curs_set(0)  # Hide cursor
    curses.use_default_colors()
    
    # Initialize color pairs
    curses.init_pair(1, curses.COLOR_BLUE, -1)      # Bot messages
    curses.init_pair(2, curses.COLOR_GREEN, -1)     # User messages
    curses.init_pair(3, curses.COLOR_WHITE, -1)     # Header
    curses.init_pair(4, curses.COLOR_YELLOW, -1)    # End marker
    curses.init_pair(5, curses.COLOR_CYAN, -1)      # Tags
    curses.init_pair(6, curses.COLOR_RED, -1)       # Unread tag
    curses.init_pair(7, curses.COLOR_WHITE, -1)  # For buttons - reverse color
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Display current conversation
        if data.conversations:
            display_conversation(stdscr, data.conversations[data.current_index], 
                                data.current_index, len(data.conversations),
                                data.scroll_position, height, width)
        else:
            stdscr.addstr(0, 0, "No conversations found.")
        
        # Handle key presses
        key = stdscr.getch()
        
        if key == ord('q'):  # Quit
            break
        elif key == ord('n') or key == ord('l') or key == curses.KEY_RIGHT:  # Next conversation
            if data.current_index < len(data.conversations) - 1:
                data.current_index += 1
                data.scroll_position = 0
        elif key == ord('p') or key == ord('h') or key == curses.KEY_LEFT:  # Previous conversation
            if data.current_index > 0:
                data.current_index -= 1
                data.scroll_position = 0
        elif key == curses.KEY_DOWN or key == ord('j'):  # Scroll down
            data.scroll_position += 1
        elif key == curses.KEY_UP or key == ord('k'):  # Scroll up
            data.scroll_position = max(0, data.scroll_position - 1)
        elif key == ord(' '):  # Page down
            data.scroll_position += height // 2
        elif key == curses.KEY_PPAGE:  # Page up
            data.scroll_position = max(0, data.scroll_position - height // 2)
        elif key == ord('g'):  # Go to top
            data.scroll_position = 0
        elif key == ord('G'):  # Go to bottom
            # This will be adjusted in display_conversation
            data.scroll_position = 9999
        # --- Search and filter ---
        elif key == ord('f'):  # Search by conversation ID
            index = search_conversation(stdscr, data.conversations, height, width)
            if index is not None:
                data.current_index = index
                data.scroll_position = 0
        elif key == ord('O'):  # Filter by tags
            index = filter_by_tags(stdscr, data.conversations, data.get_all_tags(), height, width)
            if index is not None:
                data.current_index = index
                data.scroll_position = 0
        # --- Tag management ---
        elif key == ord('r'): # Toggle read
            data.toggle_read()  # Mark as read when opening
        elif key == ord('o'):  # Manage tags
            manage_tags(stdscr, data, height, width)
        # --- Help ---
        elif key == ord('?'):  # Show help
            show_help(stdscr, height, width)
        # --- Clipboard operations ---
        elif key == ord('y'):  # Copy conversation ID
            import pyperclip
            conv_id = data.conversations[data.current_index].get("conversation_id", "N/A")
            pyperclip.copy(conv_id)
        elif key == ord('T'):  # Copy JSONL content
            import pyperclip
            # Re-serialize the current conversation data
            json_text = json.dumps(data.conversations[data.current_index])
            pyperclip.copy(json_text)

def main(filename="conversation_transcripts.jsonl"):
    """Main function to run the viewer"""
    try:
        data = ConversationData(filename)
        curses.wrapper(lambda stdscr: run_viewer(stdscr, data))
    except FileNotFoundError:
        print(f"Error: File not found - {filename}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View Botpress conversations from a JSONL file")
    parser.add_argument("--file", "-f", default="conversation_transcripts.jsonl", 
                        help="JSONL file containing conversation transcripts")
    
    args = parser.parse_args()
    main(args.file)
