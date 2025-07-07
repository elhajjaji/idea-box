from fastapi import Request


def flash(request: Request, message: str, category: str = "info"):
    """Add a flash message to the request session"""
    if not hasattr(request.state, 'flash_messages'):
        request.state.flash_messages = []
    request.state.flash_messages.append({
        'message': message,
        'category': category
    })


def get_flashed_messages(request: Request):
    """Get and clear flash messages from the request session"""
    if hasattr(request.state, 'flash_messages'):
        messages = request.state.flash_messages
        request.state.flash_messages = []
        return messages
    return []