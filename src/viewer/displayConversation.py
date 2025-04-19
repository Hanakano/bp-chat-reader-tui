# src/viewer/displayConversation.py
"""
Module for displaying a single conversation in the TUI viewer.
"""
import curses
import textwrap
import datetime
from typing import Dict, Any, List, Tuple, Union

def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display like 2025-02-23 09:23:33"""
    if not timestamp_str:
        return ""
    
    try:
        dt = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ""

def format_date(timestamp_str: str) -> str:
    """Format date in a human-readable format like April 13, 2025"""
    if not timestamp_str:
        return "Unknown date"
    
    try:
        dt = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return "Unknown date"

def format_duration(duration_minutes: float) -> str:
    """Format duration in a human-readable format"""
    if duration_minutes is None:
        return "Unknown duration"
    
    hours = int(duration_minutes // 60)
    minutes = int(duration_minutes % 60)
    seconds = int((duration_minutes * 60) % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def format_boxed_options(options: List[Dict[str, str]], max_width: int, indent: int = 4) -> List[Tuple[str, int]]:
    """Format options as boxed buttons in a horizontal layout, with wrapping if needed.
    
    Args:
        options: List of option objects with 'label' keys
        max_width: Maximum width available for rendering
        indent: Left indent for the options
        
    Returns:
        List of tuples (text, color_pair) for each line of rendered options
    """
    if not options:
        return []
    
    lines = []
    current_line = " " * indent
    button_color = 7

    for option in options:
        label = option.get('label', option.get('value', 'Option'))
        button = f"[ {label} ]  "

        if len(current_line) + len(button) > max_width:
            lines.append((current_line.rstrip(), button_color))
            current_line = " " * indent

        current_line += button

    if current_line.strip():
        lines.append((current_line.rstrip(), button_color))
    
    return lines

def display_conversation(stdscr, conversation: Dict[str, Any], 
                        current_index: int, total_conversations: int,
                        scroll_position: int, height: int, width: int) -> int:
    """Display the current conversation"""
    if not conversation:
        stdscr.addstr(0, 0, "No conversation data.")
        return 0
    
    messages = conversation.get("messages", [])
    conv_id = conversation.get("conversation_id", "Unknown ID")
    
    # Get metadata information
    metadata = conversation.get("metadata", {})
    created_date = metadata.get("createdDate", "")
    duration = metadata.get("duration", 0)
    tags = metadata.get("tags", [])
    
    # Format the date and duration
    formatted_date = format_date(created_date)
    formatted_duration = format_duration(duration)
    
    # Display header with conversation info
    header = f"Chat {current_index + 1}/{total_conversations} | ID: {conv_id}"
    meta_info = f"Date: {formatted_date} | Duration: {formatted_duration}"
    
    stdscr.attron(curses.color_pair(3))
    stdscr.addstr(0, 0, header)
    stdscr.addstr(1, 0, meta_info)
    
    # Display tags
    tag_display = "Tags: "
    tag_position = len(tag_display)
    stdscr.addstr(2, 0, tag_display)
    
    for tag in tags:
        # Use different color for unread tag
        if tag == "unread":
            stdscr.attron(curses.color_pair(6))
        else:
            stdscr.attron(curses.color_pair(5))
        
        # Check if we need to wrap to next line
        if tag_position + len(tag) + 2 > width:
            stdscr.addstr(3, 0, f"[{tag}] ")
            tag_position = len(tag) + 3
        else:
            stdscr.addstr(2, tag_position, f"[{tag}] ")
            tag_position += len(tag) + 3
        
        # Reset color
        stdscr.attroff(curses.color_pair(5))
        stdscr.attroff(curses.color_pair(6))
    
    # Add help hint
    controls_hint = "Press ? for help"
    stdscr.addstr(0, width - len(controls_hint) - 1, controls_hint)
    
    # Add horizontal rule
    stdscr.addstr(3, 0, "─" * (width - 1))
    
    # Set max width for messages
    max_width = min(width - 2, 100)
    
    # Format all messages
    message_lines = []
    
    for msg in messages:
        direction = msg.get("direction", "unknown")
        msg_type = msg.get("type", "unknown")
        timestamp = format_timestamp(msg.get("timestamp", ""))
        
        if direction == "outgoing":
            prefix = "Bot: "
            color_pair = 1
            align = "left"
        else:
            prefix = "User: "
            color_pair = 2
            align = "right"
        
        # Handle different message types
        formatted_lines = []
        formatted_lines.append((timestamp, 0))  # Timestamp with no color
        
        if msg_type in ["choice", "dropdown"]:
            # Process choice or dropdown message
            payload = msg.get("payload", {})
            text = payload.get("text", f"[{msg_type} message]")
            options = payload.get("options", [])
            
            # Wrap the main text
            wrapped_lines = textwrap.wrap(text, width=max_width - len(prefix))
            
            # Add the prefix to the first line
            for i, line in enumerate(wrapped_lines):
                if i == 0:
                    formatted_lines.append((f"{prefix}{line}", color_pair, align))
                else:
                    formatted_lines.append((f"{'':>{len(prefix)}}{line}", color_pair, align))
            
            # Add a separator before options
            formatted_lines.append(("", 0))
            
            # Add the options as boxed buttons
            option_lines = format_boxed_options(options, max_width, len(prefix))
            formatted_lines.extend([(text, color) for text, color in option_lines])
            
        else:
            # Process regular text message
            text = msg.get("text", "")
            if not text and "payload" in msg and "text" in msg["payload"]:
                text = msg["payload"]["text"]
                
            if not text:
                text = f"[{msg_type} message]"
                
            # Wrap text to fit screen
            wrapped_lines = textwrap.wrap(text, width=max_width - len(prefix))
            if not wrapped_lines:
                wrapped_lines = ["[Empty message]"]
                
            # Format with prefix on first line
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
    max_scroll = max(0, total_lines - (height - 6))  # Adjust for header and footer
    if scroll_position > max_scroll:
        scroll_position = max_scroll
        
    # Display messages with scrolling
    current_line = 4  # Start after header, metadata, tags, and rule
    line_counter = 0
    
    for msg_lines in message_lines:
        for line_data in msg_lines:
            if len(line_data) == 2:  # It's a timestamp
                text, color = line_data
                align = "left"
            else:  # It's a message line or end marker
                text, color, align = line_data
            
            # Check if this line should be displayed based on scroll position
            if line_counter >= scroll_position and current_line < height - 1:
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
        scroll_percent = min(100, int((scroll_position / max_scroll) * 100))
        scroll_indicator = f"Scroll: {scroll_percent}% "
        stdscr.addstr(height - 1, width - len(scroll_indicator) - 1, scroll_indicator)
    
    return max_scroll  # Return the maximum scroll position
