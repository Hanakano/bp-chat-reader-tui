# src/viewer/filter_conversation.py
"""
Module for filtering conversations by tags in the TUI viewer.
"""
import curses
from typing import List, Dict, Any, Optional

def filter_by_tags(stdscr, conversations: List[Dict[str, Any]], all_tags: List[str], height: int, width: int) -> Optional[int]:
    """Filter conversations by tags and select one to view"""
    # First, get the tag filter from the user
    tag_filter = get_tag_filter(stdscr, all_tags, height, width)
    if not tag_filter:
        return None
        
    # Find conversations matching the tag filter
    matching_conversations = []
    for i, conv in enumerate(conversations):
        if "metadata" in conv and "tags" in conv["metadata"]:
            if tag_filter in conv["metadata"]["tags"]:
                matching_conversations.append((i, conv))
    
    if not matching_conversations:
        # Show "No matches" message
        box_height = 3
        box_width = 40
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        message_box = curses.newwin(box_height, box_width, start_y, start_x)
        message_box.box()
        message_box.addstr(1, 2, f"No conversations with tag '{tag_filter}'")
        message_box.refresh()
        message_box.getch()  # Wait for any key
        return None
    
    # Show list of matching conversations
    return display_conversation_list(stdscr, matching_conversations, height, width)

def get_tag_filter(stdscr, all_tags: List[str], height: int, width: int) -> Optional[str]:
    """Display an input box for tag filtering"""
    # Calculate box dimensions
    box_height = 6  # One extra line to show available tags
    box_width = 60
    start_y = (height - box_height) // 2
    start_x = (width - box_width) // 2
    
    # Create search box
    search_box = curses.newwin(box_height, box_width, start_y, start_x)
    search_box.box()
    search_box.addstr(1, 2, "Filter conversations by tag:")
    search_box.addstr(2, 2, " " * (box_width - 4))  # Input area
    
    # Show available tags
    available_tags = ", ".join(all_tags) if all_tags else "No tags available"
    # Truncate if too long
    if len(available_tags) > box_width - 15:
        available_tags = available_tags[:box_width - 18] + "..."
    search_box.addstr(3, 2, f"Tags: {available_tags}")
    
    search_box.addstr(4, 2, "Press Enter to filter, Esc to cancel")
    search_box.refresh()
    
    # Create input window inside the box
    input_win = curses.newwin(1, box_width - 6, start_y + 2, start_x + 3)
    curses.echo()  # Show typed characters
    curses.curs_set(1)  # Show cursor
    
    # Get input
    filter_text = ""
    while True:
        input_win.clear()
        input_win.addstr(0, 0, filter_text)
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
            if filter_text:
                filter_text = filter_text[:-1]
        elif key == curses.KEY_RESIZE:
            # Handle terminal resize
            height, width = stdscr.getmaxyx()
            start_y = (height - box_height) // 2
            start_x = (width - box_width) // 2
            search_box.mvwin(start_y, start_x)
            input_win.mvwin(start_y + 2, start_x + 3)
            search_box.refresh()
        elif 32 <= key <= 126:  # Printable characters
            filter_text += chr(key)
    
    # Reset terminal settings
    curses.noecho()
    curses.curs_set(0)
    
    # Return the filter text if Enter was pressed
    if key == 10 and filter_text.strip():
        return filter_text.strip()
    return None

def display_conversation_list(stdscr, matching_conversations: List[tuple], height: int, width: int) -> Optional[int]:
    """Display a list of matching conversations and let user select one"""
    if not matching_conversations:
        return None
        
    # Calculate box dimensions
    list_count = min(len(matching_conversations), height - 6)
    box_height = list_count + 4  # Header, footer, and margins
    box_width = min(100, width - 4)
    start_y = (height - box_height) // 2
    start_x = (width - box_width) // 2
    
    # Create list window
    list_box = curses.newwin(box_height, box_width, start_y, start_x)
    list_box.box()
    list_box.addstr(1, 2, f"Found {len(matching_conversations)} matching conversations:")
    list_box.addstr(box_height - 2, 2, "Press Enter to select, Esc to cancel")
    list_box.refresh()
    
    # Create scrollable list window
    list_win = curses.newwin(list_count, box_width - 4, start_y + 2, start_x + 2)
    
    current_selection = 0
    scroll_offset = 0
    
    while True:
        list_win.clear()
        
        # Display visible items
        for i in range(min(list_count, len(matching_conversations) - scroll_offset)):
            index = i + scroll_offset
            conv_index, conv = matching_conversations[index]
            
            # Format conversation information
            conv_id = conv.get("conversation_id", "Unknown ID")
            tags = conv.get("metadata", {}).get("tags", [])
            tag_str = ", ".join(tags) if tags else "No tags"
            
            # Truncate if too long
            max_id_len = 20
            max_tag_len = box_width - max_id_len - 15
            
            if len(conv_id) > max_id_len:
                conv_id = conv_id[:max_id_len-3] + "..."
            if len(tag_str) > max_tag_len:
                tag_str = tag_str[:max_tag_len-3] + "..."
                
            display_text = f"{conv_id:<{max_id_len}} | Tags: {tag_str}"
            
            # Highlight selected item
            if index == current_selection:
                list_win.attron(curses.A_REVERSE)
                list_win.addstr(i, 0, display_text)
                list_win.attroff(curses.A_REVERSE)
            else:
                list_win.addstr(i, 0, display_text)
        
        list_win.refresh()
        
        # Handle key presses
        key = stdscr.getch()
        
        if key == 27:  # Escape key
            break
        elif key == 10:  # Enter key
            # Return the index of the selected conversation
            return matching_conversations[current_selection][0]
        elif key == curses.KEY_DOWN or key == ord('j'):  # Next item
            if current_selection < len(matching_conversations) - 1:
                current_selection += 1
                # Scroll if needed
                if current_selection >= scroll_offset + list_count:
                    scroll_offset += 1
        elif key == curses.KEY_UP or key == ord('k'):  # Previous item
            if current_selection > 0:
                current_selection -= 1
                # Scroll if needed
                if current_selection < scroll_offset:
                    scroll_offset -= 1
        elif key == curses.KEY_RESIZE:
            # Handle terminal resize
            height, width = stdscr.getmaxyx()
            list_count = min(len(matching_conversations), height - 6)
            box_height = list_count + 4
            box_width = min(100, width - 4)
            start_y = (height - box_height) // 2
            start_x = (width - box_width) // 2
            
            list_box.resize(box_height, box_width)
            list_box.mvwin(start_y, start_x)
            list_win.resize(list_count, box_width - 4)
            list_win.mvwin(start_y + 2, start_x + 2)
            list_box.box()
            list_box.addstr(1, 2, f"Found {len(matching_conversations)} matching conversations:")
            list_box.addstr(box_height - 2, 2, "Press Enter to select, Esc to cancel")
            list_box.refresh()
    
    return None
