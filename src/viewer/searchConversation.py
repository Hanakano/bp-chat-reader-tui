# src/viewer/search_conversation.py
"""
Module for searching conversations by ID in the TUI viewer.
"""
import curses
from typing import List, Dict, Any, Optional

def search_conversation(stdscr, conversations: List[Dict[str, Any]], height: int, width: int) -> Optional[int]:
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
                import pyperclip
                pasted_text = pyperclip.paste()
                search_text += pasted_text
            except:
                pass
    
    # Reset terminal settings
    curses.noecho()
    curses.curs_set(0)
    
    # If Enter was pressed and we have a search term, perform search
    if key == 10 and search_text.strip():
        result_index = find_conversation_by_id(conversations, search_text.strip())
        if result_index is not None:
            return result_index
        else:
            # Show "Not found" message
            search_box.clear()
            search_box.box()
            search_box.addstr(2, (box_width - 22) // 2, "Conversation not found")
            search_box.refresh()
            search_box.getch()  # Wait for any key
            
    return None

def find_conversation_by_id(conversations: List[Dict[str, Any]], conversation_id: str) -> Optional[int]:
    """Find conversation index by ID"""
    for i, conversation in enumerate(conversations):
        if conversation.get("conversation_id") == conversation_id:
            return i
    return None
