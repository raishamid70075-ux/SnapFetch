def format_duration(seconds) -> str:
    """Mengubah durasi dari detik ke format MM:SS atau HH:MM:SS"""
    if not seconds:
        return "00:00"
        
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return "00:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes:02d}:{remaining_seconds:02d}"