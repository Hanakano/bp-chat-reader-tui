# src/viewChats.py
"""
TUI Viewer for Botpress Conversation Transcripts in JSONL format.

Displays conversations from a JSONL file in a terminal user interface,
allowing navigation between conversations and scrolling through messages.
Provides options to copy conversation IDs or the full JSONL data to the clipboard.
"""
import json
import os
import curses
import datetime
import textwrap
import pyperclip

class ConversationViewer:
    def __init__(self, filename):
        self.filename = filename
        self.conversations = []
        self.current_index = 0
        self.scroll_position = 0
        self.max_width = 80  # Default width
        self.load_conversations()
        
    def load_conversations(self):
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
            
    def format_timestamp(self, timestamp_str):
        """Format timestamp for display"""
        if not timestamp_str:
            return ""
        
        try:
            dt = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return ""
    
    def search_conversation(self, stdscr, height, width):
        """Display a search box and find conversation by ID"""
        # Calculate box dimensions
        box_height = 5
        box_width = 60
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Create search box
        search_box = curses.newwin(box_height, box_width, start_y, start_x)
        search_box.box()
        search_box.addstr(1, 2, "Search for Conversation ID:")
        search_box.addstr(2, 2, " " * (box_width - 4))  # Input area
        search_box.addstr(3, 2, "Press Enter to search, Esc to cancel")
        search_box.refresh()
        
        # Create input window inside the box
        input_win = curses.newwin(1, box_width - 6, start_y + 2, start_x + 3)
        curses.echo()  # Show typed characters
        curses.curs_set(1)  # Show cursor
        key = 0
        
        # Get input
        search_text = ""
        while True:
            input_win.clear()
            input_win.addstr(0, 0, search_text)
            input_win.refresh()
            
            try:
                key = input_win.getch()
            except KeyboardInterrupt:
                break
                
            if key == 27:  # Escape key
                break
            elif key == 10:  # Enter key
                break
            elif key == curses.KEY_BACKSPACE or key == 127:  # Backspace key
                if search_text:
                    search_text = search_text[:-1]
            elif key == curses.KEY_RESIZE:
                # Handle terminal resize
                height, width = stdscr.getmaxyx()
                start_y = (height - box_height) // 2
                start_x = (width - box_width) // 2
                search_box.mvwin(start_y, start_x)
                input_win.mvwin(start_y + 2, start_x + 3)
                search_box.refresh()
            elif 32 <= key <= 126:  # Printable characters
                search_text += chr(key)
            elif key == 22:  # Ctrl+V for paste
                try:
                    pasted_text = pyperclip.paste()
                    search_text += pasted_text
                except:
                    pass
        
        # Reset terminal settings
        curses.noecho()
        curses.curs_set(0)
        
        # If Enter was pressed and we have a search term, perform search
        if key == 10 and search_text.strip():
            result_index = self.find_conversation_by_id(search_text.strip())
            if result_index is not None:
                self.current_index = result_index
                self.scroll_position = 0
                return True
            else:
                # Show "Not found" message
                search_box.clear()
                search_box.box()
                search_box.addstr(2, (box_width - 22) // 2, "Conversation not found")
                search_box.refresh()
                search_box.getch()  # Wait for any key
                
        return False
        
    def find_conversation_by_id(self, conversation_id):
        """Find conversation index by ID"""
        for i, conversation in enumerate(self.conversations):
            if conversation.get("conversation_id") == conversation_id:
                return i
        return None
            
    def run(self, stdscr):
        """Run the TUI viewer"""
        curses.curs_set(0)  # Hide cursor
        curses.use_default_colors()
        
        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_BLUE, -1)  # Bot messages
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # User messages
        curses.init_pair(3, curses.COLOR_WHITE, -1)  # Header
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # End marker
        
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            self.max_width = min(width - 2, 100)  # Set max width for messages
            
            self.display_conversation(stdscr, height, width)
            
            # Handle key presses
            key = stdscr.getch()
            
            if key == ord('q'):  # Quit
                break
            elif key == ord('n') or key == ord('l') or key == curses.KEY_RIGHT:  # Next conversation (vim bindings added)
                if self.current_index < len(self.conversations) - 1:
                    self.current_index += 1
                    self.scroll_position = 0
            elif key == ord('p') or key == ord('h') or key == curses.KEY_LEFT:  # Previous conversation (vim bindings added)
                if self.current_index > 0:
                    self.current_index -= 1
                    self.scroll_position = 0
            elif key == curses.KEY_DOWN or key == ord('j'):  # Scroll down (vim binding added)
                self.scroll_position += 1
            elif key == curses.KEY_UP or key == ord('k'):  # Scroll up (vim binding added)
                self.scroll_position = max(0, self.scroll_position - 1)
            elif key == ord(' '):  # Page down
                self.scroll_position += height // 2
            elif key == curses.KEY_PPAGE:  # Page up
                self.scroll_position = max(0, self.scroll_position - height // 2)
            elif key == ord('g'):  # Go to top
                self.scroll_position = 0
            elif key == ord('G'):  # Go to bottom
                # This will be adjusted in display_conversation
                self.scroll_position = 9999
            # --- Clipboard ---
            elif key == ord('y'): # Copy Conversation ID
                conv_id = self.conversations[self.current_index].get("conversation_id", "N/A")
                pyperclip.copy(conv_id)
            elif key == ord('T'): # Copy JSONL content
                # Re-serialize the current conversation data
                json_text = json.dumps(self.conversations[self.current_index])
                pyperclip.copy(json_text)
            # --- Search ---
            elif key == ord('f'):  # Trigger search
                self.search_conversation(stdscr, height, width)
    
    def display_conversation(self, stdscr, height, width):
        """Display the current conversation"""
        if not self.conversations:
            stdscr.addstr(0, 0, "No conversations found.")
            return
            
        conversation = self.conversations[self.current_index]
        messages = conversation.get("messages", [])
        conv_id = conversation.get("conversation_id", "Unknown ID")
        
        # Display header with horizontal rule instead of background color
        header = f"Conversation {self.current_index + 1}/{len(self.conversations)} | ID: {conv_id}"
        controls = "h/l:Prev/Next j/k:Up/Down g/G:Top/Bottom f:Search q:Quit"
        
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(0, 0, header)
        stdscr.addstr(0, width - len(controls) - 1, controls)
        stdscr.attroff(curses.color_pair(3))
        
        # Add horizontal rule
        stdscr.addstr(1, 0, "─" * (width - 1))
        
        # Calculate start position for messages
        line_count = 3  # Start after header, horizontal rule, and a blank line
        message_lines = []
        
        # Format all messages and calculate total lines
        for msg in messages:
            direction = msg.get("direction", "unknown")
            msg_type = msg.get("type", "unknown")
            text = msg.get("text", f"[{msg_type} message]")
            timestamp = self.format_timestamp(msg.get("timestamp", ""))
            
            if direction == "outgoing":
                prefix = "Bot: "
                color_pair = 1
                align = "left"
            else:
                prefix = "User: "
                color_pair = 2
                align = "right"
            
            # Wrap text to fit screen
            wrapped_lines = textwrap.wrap(text, width=self.max_width - len(prefix))
            if not wrapped_lines:
                wrapped_lines = ["[Empty message]"]
                
            # Format: timestamp, prefix, and message
            formatted_lines = []
            formatted_lines.append((timestamp, 0))  # Timestamp with no color
            
            for i, line in enumerate(wrapped_lines):
                if i == 0:  # First line includes the prefix
                    formatted_lines.append((f"{prefix}{line}", color_pair, align))
                else:
                    # Indent continuation lines
                    formatted_lines.append((f"{'':>{len(prefix)}}{line}", color_pair, align))
                    
            message_lines.append(formatted_lines)
            
        # Add chat end marker
        end_marker_lines = [("", 0), ("<<< CHAT END >>>", 4, "center")]
        message_lines.append(end_marker_lines)
        
        # Calculate total lines needed
        total_lines = sum(len(msg) for msg in message_lines)
        
        # Adjust scroll position if needed
        max_scroll = max(0, total_lines - (height - 4))
        if self.scroll_position > max_scroll:
            self.scroll_position = max_scroll
            
        # Display messages with scrolling
        current_line = 3  # Start after header, horizontal rule and a blank line
        line_counter = 0
        
        for msg_lines in message_lines:
            for line_data in msg_lines:
                if len(line_data) == 2:  # It's a timestamp
                    text, color = line_data
                    align = "left"
                else:  # It's a message line or end marker
                    text, color, align = line_data
                
                # Check if this line should be displayed based on scroll position
                if line_counter >= self.scroll_position and current_line < height - 1:
                    if align == "right":
                        # Right-align text, but leave room for the timestamp
                        position = max(0, width - len(text) - 2)
                    elif align == "center":
                        # Center the text
                        position = max(0, (width - len(text)) // 2)
                    else:
                        position = 2
                        
                    if color:
                        stdscr.attron(curses.color_pair(color))
                    stdscr.addstr(current_line, position, text)
                    if color:
                        stdscr.attroff(curses.color_pair(color))
                        
                    current_line += 1
                    
                line_counter += 1
                
        # Display scroll indicator if needed
        if max_scroll > 0:
            scroll_percent = min(100, int((self.scroll_position / max_scroll) * 100))
            scroll_indicator = f"Scroll: {scroll_percent}% "
            stdscr.addstr(height - 1, width - len(scroll_indicator) - 1, scroll_indicator)

def main(filename="conversation_transcripts.jsonl"):
    """Main function to run the viewer"""
    try:
        viewer = ConversationViewer(filename)
        curses.wrapper(viewer.run)
    except FileNotFoundError:
        print(f"Error: File not found - {filename}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="View Botpress conversations from a JSONL file")
    parser.add_argument("--file", "-f", default="conversation_transcripts.jsonl", 
                        help="JSONL file containing conversation transcripts")
    
    args = parser.parse_args()
    main(args.file)
