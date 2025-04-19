# src/viewer/helpWindow.py
"""
Module for displaying help information in the TUI viewer.
"""
import curses
from typing import List

def show_help(stdscr, height: int, width: int) -> None:
    """Display help window with keyboard shortcuts"""
    # Define help text lines
    help_lines = [
        "Keyboard Shortcuts",
        "=================",
        "",
        "Navigation:",
        "h, l, ←, →       Previous/Next conversation",
        "j, k, ↑, ↓       Scroll up/down",
        "Space            Page down",
        "PgUp             Page up",
        "g                Go to top",
        "G                Go to bottom",
        "",
        "Search and Filter:",
        "f                Search for conversation by ID",
        "O                Search conversations by tag",
        "",
        "Tag Management:",
        "r                Toggle read/unread",
        "o                Manage tags for current conversation",
        "",
        "Clipboard:",
        "y                Copy current conversation ID",
        "T                Copy full conversation JSON",
        "",
        "Other:",
        "?                Show this help",
        "q                Quit"
    ]
    
    # Calculate box dimensions
    box_height = min(len(help_lines) + 4, height - 4)
    box_width = min(60, width - 4)
    start_y = (height - box_height) // 2
    start_x = (width - box_width) // 2
    
    # Create help window
    help_box = curses.newwin(box_height, box_width, start_y, start_x)
    help_box.box()
    help_box.addstr(box_height - 2, 2, "Press Escape to close")
    
    # Create scrollable content window
    content_height = box_height - 3
    content_win = curses.newwin(content_height, box_width - 4, start_y + 1, start_x + 2)
    
    # Handle scrolling
    scroll_position = 0
    max_scroll = max(0, len(help_lines) - content_height)
    
    while True:
        content_win.clear()
        
        # Display visible help lines
        for i in range(min(content_height, len(help_lines) - scroll_position)):
            line_index = i + scroll_position
            if line_index < len(help_lines):
                content_win.addstr(i, 0, help_lines[line_index])
        
        # Show scroll indicator if needed
        if max_scroll > 0:
            help_box.addstr(box_height - 2, box_width - 15, 
                           f"Scroll: {scroll_position}/{max_scroll}")
        
        help_box.refresh()
        content_win.refresh()
        
        # Handle key presses
        key = stdscr.getch()
        
        if key == 27 or key == ord('q') or key == ord('?'):  # Escape, q, or ? to close
            break
        elif key == curses.KEY_DOWN or key == ord('j'):  # Scroll down
            if scroll_position < max_scroll:
                scroll_position += 1
        elif key == curses.KEY_UP or key == ord('k'):  # Scroll up
            if scroll_position > 0:
                scroll_position -= 1
        elif key == ord(' '):  # Page down
            scroll_position = min(max_scroll, scroll_position + content_height - 1)
        elif key == curses.KEY_PPAGE:  # Page up
            scroll_position = max(0, scroll_position - (content_height - 1))
        elif key == ord('g'):  # Go to top
            scroll_position = 0
        elif key == ord('G'):  # Go to bottom
            scroll_position = max_scroll
        elif key == curses.KEY_RESIZE:
            # Handle terminal resize
            height, width = stdscr.getmaxyx()
            box_height = min(len(help_lines) + 4, height - 4)
            box_width = min(60, width - 4)
            start_y = (height - box_height) // 2
            start_x = (width - box_width) // 2
            
            help_box.resize(box_height, box_width)
            help_box.mvwin(start_y, start_x)
            
            content_height = box_height - 3
            content_win.resize(content_height, box_width - 4)
            content_win.mvwin(start_y + 1, start_x + 2)
            
            help_box.box()
            help_box.addstr(box_height - 2, 2, "Press any key to close")
            
            # Recalculate max scroll
            max_scroll = max(0, len(help_lines) - content_height)
            if scroll_position > max_scroll:
                scroll_position = max_scroll
