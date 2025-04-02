from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json

# Admin model functions
def create_admin(conn, username: str, password_hash: str) -> int:
    """Create a new admin and return its ID"""
    cursor = conn.execute(
        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    return cursor.lastrowid

def get_admin_by_username(conn, username: str) -> Optional[Dict]:
    """Get admin by username"""
    row = conn.execute(
        "SELECT id, username, password_hash FROM admins WHERE username = ?",
        (username,)
    ).fetchone()
    
    if not row:
        return None
    
    return {
        'id': row[0],
        'username': row[1],
        'password_hash': row[2]
    }

def update_admin_password(conn, admin_id: int, password_hash: str) -> bool:
    """Update admin password"""
    conn.execute(
        "UPDATE admins SET password_hash = ? WHERE id = ?",
        (password_hash, admin_id)
    )
    return True

# OTP model functions
def create_otp(conn, code: str, max_uses: int = 5, expires_at: Optional[datetime] = None) -> int:
    """Create a new OTP and return its ID"""
    expires_at_str = expires_at.isoformat() if expires_at else None
    
    cursor = conn.execute(
        """
        INSERT INTO otps (code, max_uses, remaining_uses, is_used, created_at, expires_at) 
        VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP, ?)
        """,
        (code, max_uses, max_uses, expires_at_str)
    )
    return cursor.lastrowid

def get_otp_by_code(conn, code: str) -> Optional[Dict]:
    """Get OTP by code"""
    row = conn.execute(
        """
        SELECT id, code, max_uses, remaining_uses, is_used, created_at, expires_at
        FROM otps WHERE code = ?
        """,
        (code,)
    ).fetchone()
    
    if not row:
        return None
    
    # Parse datetime strings
    created_at = datetime.fromisoformat(row[5]) if row[5] else None
    expires_at = datetime.fromisoformat(row[6]) if row[6] else None
    
    return {
        'id': row[0],
        'code': row[1],
        'max_uses': row[2],
        'remaining_uses': row[3],
        'is_used': bool(row[4]),
        'created_at': created_at,
        'expires_at': expires_at
    }

def update_otp_usage(conn, otp_id: int) -> bool:
    """Update OTP usage count, setting is_used if no uses remain"""
    # First get current usage
    row = conn.execute(
        "SELECT remaining_uses FROM otps WHERE id = ?",
        (otp_id,)
    ).fetchone()
    
    if not row:
        return False
    
    remaining = row[0] - 1
    is_used = 1 if remaining <= 0 else 0
    
    conn.execute(
        "UPDATE otps SET remaining_uses = ?, is_used = ? WHERE id = ?",
        (remaining, is_used, otp_id)
    )
    return True

def get_all_otps(conn, limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
    """Get all OTPs with pagination, returns (otps, total_count)"""
    # Get total count
    total = conn.execute("SELECT COUNT(*) FROM otps").fetchone()[0]
    
    # Get paginated results
    rows = conn.execute(
        """
        SELECT id, code, max_uses, remaining_uses, is_used, created_at, expires_at
        FROM otps
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset)
    ).fetchall()
    
    result = []
    for row in rows:
        # Parse datetime strings
        created_at = datetime.fromisoformat(row[5]) if row[5] else None
        expires_at = datetime.fromisoformat(row[6]) if row[6] else None
        
        result.append({
            'id': row[0],
            'code': row[1],
            'max_uses': row[2],
            'remaining_uses': row[3],
            'is_used': bool(row[4]),
            'created_at': created_at,
            'expires_at': expires_at
        })
    
    return result, total

# OTP Usage model functions
def record_otp_usage(conn, otp_id: int, agent_type: str) -> int:
    """Record OTP usage and return the usage ID"""
    cursor = conn.execute(
        """
        INSERT INTO otp_usages (otp_id, agent_type, timestamp)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        """,
        (otp_id, agent_type)
    )
    return cursor.lastrowid

def get_otp_usages(conn, limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
    """Get OTP usages with pagination, returns (usages, total_count)"""
    # Get total count
    total = conn.execute("SELECT COUNT(*) FROM otp_usages").fetchone()[0]
    
    # Get paginated results
    rows = conn.execute(
        """
        SELECT id, otp_id, agent_type, timestamp
        FROM otp_usages
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset)
    ).fetchall()
    
    result = []
    for row in rows:
        result.append({
            'id': row[0],
            'otp_id': row[1],
            'agent_type': row[2],
            'timestamp': datetime.fromisoformat(row[3]) if row[3] else None
        })
    
    return result, total

# Agent Traffic model functions
def record_agent_traffic(conn, agent_type: str) -> int:
    """Record or update agent traffic and return the traffic ID"""
    # Check if entry exists
    row = conn.execute(
        "SELECT id, session_count FROM agent_traffic WHERE agent_type = ?",
        (agent_type,)
    ).fetchone()
    
    if row:
        # Update existing entry
        traffic_id, session_count = row
        conn.execute(
            """
            UPDATE agent_traffic 
            SET session_count = ?, last_activity = CURRENT_TIMESTAMP 
            WHERE id = ?
            """,
            (session_count + 1, traffic_id)
        )
        return traffic_id
    else:
        # Create new entry
        cursor = conn.execute(
            """
            INSERT INTO agent_traffic (agent_type, session_count, last_activity, is_active)
            VALUES (?, 1, CURRENT_TIMESTAMP, 1)
            """,
            (agent_type,)
        )
        return cursor.lastrowid

def get_agent_traffic(conn, limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
    """Get agent traffic with pagination, returns (traffic_data, total_count)"""
    # Get total count
    total = conn.execute("SELECT COUNT(*) FROM agent_traffic").fetchone()[0]
    
    # Get paginated results
    rows = conn.execute(
        """
        SELECT id, agent_type, session_count, last_activity, is_active
        FROM agent_traffic
        ORDER BY last_activity DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset)
    ).fetchall()
    
    result = []
    for row in rows:
        result.append({
            'id': row[0],
            'agent_type': row[1],
            'session_count': row[2],
            'last_activity': datetime.fromisoformat(row[3]) if row[3] else None,
            'is_active': bool(row[4])
        })
    
    return result, total 