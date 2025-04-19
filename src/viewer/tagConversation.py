# src/viewer/tagConversation.py
"""
Module for managing tags in the TUI viewer.
"""
import curses
from typing import List, Dict, Any, Optional

def manage_tags(stdscr, data, height: int, width: int) -> None:
    """Display a window for managing tags of the current conversation"""
    if not data.conversations or data.current_index >= len(data.conversations):
        return
        
    # Get current conversation and its tags
    conversation = data.conversations[data.current_index]
    if "metadata" not in conversation:
        conversation["metadata"] = {}
    if "tags" not in conversation["metadata"]:
        conversation["metadata"]["tags"] = []
        
    current_tags = conversation["metadata"]["tags"]
    
    # Get all unique tags from all conversations
    all_tags = data.get_all_tags()
    
    # Add a special "Create new tag" option
    display_tags = all_tags + ["+ Create new tag"]
    
    # Calculate box dimensions
    list_count = min(len(display_tags), height - 6)
    box_height = list_count + 4  # Header, footer, and margins
    box_width = min(60, width - 4)
    start_y = (height - box_height) // 2
    start_x = (width - box_width) // 2
    
    # Create tag management window
    tag_box = curses.newwin(box_height, box_width, start_y, start_x)
    tag_box.box()
    tag_box.addstr(1, 2, "Manage Tags (Space to toggle, Enter when done):")
    tag_box.refresh()
    
    # Create scrollable list window
    list_win = curses.newwin(list_count, box_width - 4, start_y + 2, start_x + 2)
    
    current_selection = 0
    scroll_offset = 0
    
    while True:
        list_win.clear()
        
        # Display visible items
        for i in range(min(list_count, len(display_tags) - scroll_offset)):
            index = i + scroll_offset
            tag = display_tags[index]
            
            # Check if this is the "Create new tag" option
            if tag == "+ Create new tag":
                display_text = tag
            else:
                # Show checkbox to indicate if tag is applied
                checkbox = "[X]" if tag in current_tags else "[ ]"
                display_text = f"{checkbox} {tag}"
            
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
            # If "Create new tag" is selected, prompt for new tag
            if current_selection == len(display_tags) - 1:
                new_tag = prompt_for_new_tag(stdscr, height, width)
                if new_tag and new_tag not in all_tags:
                    data.add_tag(new_tag)
                    return
            break
        elif key == ord(' '):  # Space to toggle tag
            # Skip for "Create new tag" option
            if current_selection < len(display_tags) - 1:
                tag = display_tags[current_selection]
                if tag in current_tags:
                    data.remove_tag(tag)
                    current_tags.remove(tag)
                else:
                    data.add_tag(tag)
                    current_tags.append(tag)
        elif key == curses.KEY_DOWN or key == ord('j'):  # Next item
            if current_selection < len(display_tags) - 1:
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
            list_count = min(len(display_tags), height - 6)
            box_height = list_count + 4
            box_width = min(60, width - 4)
            start_y = (height - box_height) // 2
            start_x = (width - box_width) // 2
            
            tag_box.resize(box_height, box_width)
            tag_box.mvwin(start_y, start_x)
            list_win.resize(list_count, box_width - 4)
            list_win.mvwin(start_y + 2, start_x + 2)
            tag_box.box()
            tag_box.addstr(1, 2, "Manage Tags (Space to toggle, Enter when done):")
            tag_box.refresh()

def prompt_for_new_tag(stdscr, height: int, width: int) -> Optional[str]:
    """Display an input box for creating a new tag"""
    # Calculate box dimensions
    box_height = 5
    box_width = 50
    start_y = (height - box_height) // 2
    start_x = (width - box_width) // 2
    
    # Create input box
    input_box = curses.newwin(box_height, box_width, start_y, start_x)
    input_box.box()
    input_box.addstr(1, 2, "Enter new tag name:")
    input_box.addstr(2, 2, " " * (box_width - 4))  # Input area
    input_box.addstr(3, 2, "Press Enter to save, Esc to cancel")
    input_box.refresh()
    
    # Create input window inside the box
    input_win = curses.newwin(1, box_width - 6, start_y + 2, start_x + 3)
    curses.echo()  # Show typed characters
    curses.curs_set(1)  # Show cursor
    
    # Get input
    tag_text = ""
    key = 0
    while True:
        input_win.clear()
        input_win.addstr(0, 0, tag_text)
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
            if tag_text:
                tag_text = tag_text[:-1]
        elif key == curses.KEY_RESIZE:
            # Handle terminal resize
            height, width = stdscr.getmaxyx()
            start_y = (height - box_height) // 2
            start_x = (width - box_width) // 2
            input_box.mvwin(start_y, start_x)
            input_win.mvwin(start_y + 2, start_x + 3)
            input_box.refresh()
        elif 32 <= key <= 126:  # Printable characters (no spaces at beginning)
            if tag_text or key != 32:  # Skip space at beginning
                tag_text += chr(key)
    
    # Reset terminal settings
    curses.noecho()
    curses.curs_set(0)
    
    # Return the tag text if Enter was pressed and text isn't empty
    if key == 10 and tag_text.strip():
        return tag_text.strip()
    return None
