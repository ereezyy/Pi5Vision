#!/usr/bin/env python3
"""
Database Manager for Pi5 Face Recognition System
Handles database initialization, migrations, and operations
"""

import os
import sys
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import base64

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Production database manager with initialization and migration support
    """
    
    def __init__(self, db_path: str = "/opt/pi5-face-recognition/database/faces.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.schema_version = 3  # Current schema version
        
        logger.info(f"Database manager initialized: {db_path}")
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
            self.conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def initialize_database(self):
        """Initialize database with schema"""
        if not self.connect():
            return False
        
        try:
            # Check if database exists and get version
            current_version = self._get_schema_version()
            
            if current_version == 0:
                # New database - create all tables
                logger.info("Creating new database schema...")
                self._create_initial_schema()
                self._set_schema_version(self.schema_version)
            elif current_version < self.schema_version:
                # Need to migrate
                logger.info(f"Migrating database from version {current_version} to {self.schema_version}")
                self._migrate_schema(current_version, self.schema_version)
            else:
                logger.info(f"Database schema up to date (version {current_version})")
            
            # Create indexes
            self._create_indexes()
            
            # Insert default data if needed
            self._insert_default_data()
            
            self.conn.commit()
            logger.info("Database initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            self.disconnect()
    
    def _create_initial_schema(self):
        """Create initial database schema"""
        # Persons table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL DEFAULT (lower(hex(randomblob(16)))),
                name TEXT NOT NULL,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                visit_count INTEGER DEFAULT 0,
                notes TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Face embeddings table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                embedding_data BLOB NOT NULL,
                embedding_version TEXT DEFAULT 'arcface_v1',
                image_path TEXT,
                quality_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (person_id) REFERENCES persons (id) ON DELETE CASCADE
            )
        ''')
        
        # Visits table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0.0,
                camera_id TEXT DEFAULT 'camera_0',
                image_path TEXT,
                location TEXT,
                additional_data TEXT,
                FOREIGN KEY (person_id) REFERENCES persons (id) ON DELETE SET NULL
            )
        ''')
        
        # Alerts table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                alert_type TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                processed_at TIMESTAMP,
                processed_by TEXT,
                image_path TEXT,
                additional_data TEXT,
                FOREIGN KEY (person_id) REFERENCES persons (id) ON DELETE SET NULL
            )
        ''')
        
        # System events table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'system'
            )
        ''')
        
        # Configuration table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Schema version table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_info (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_persons_name ON persons (name)",
            "CREATE INDEX IF NOT EXISTS idx_persons_uuid ON persons (uuid)",
            "CREATE INDEX IF NOT EXISTS idx_persons_last_seen ON persons (last_seen)",
            "CREATE INDEX IF NOT EXISTS idx_face_embeddings_person_id ON face_embeddings (person_id)",
            "CREATE INDEX IF NOT EXISTS idx_visits_person_id ON visits (person_id)",
            "CREATE INDEX IF NOT EXISTS idx_visits_timestamp ON visits (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_processed ON alerts (processed)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts (alert_type)",
            "CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events (event_type)"
        ]
        
        for index_sql in indexes:
            try:
                self.conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")
    
    def _insert_default_data(self):
        """Insert default configuration data"""
        default_config = [
            ('system_initialized', 'true', 'System initialization flag'),
            ('db_version', str(self.schema_version), 'Database schema version'),
            ('installation_date', datetime.now().isoformat(), 'Installation timestamp'),
            ('face_detection_enabled', 'true', 'Enable face detection'),
            ('face_recognition_enabled', 'true', 'Enable face recognition'),
            ('alert_unknown_faces', 'true', 'Alert on unknown faces'),
            ('retention_days', '30', 'Data retention period in days'),
            ('max_persons', '1000', 'Maximum number of persons to store')
        ]
        
        for key, value, description in default_config:
            self.conn.execute('''
                INSERT OR IGNORE INTO configuration (key, value, description)
                VALUES (?, ?, ?)
            ''', (key, value, description))
    
    def _get_schema_version(self) -> int:
        """Get current schema version"""
        try:
            cursor = self.conn.execute("SELECT version FROM schema_info ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else 0
        except:
            return 0
    
    def _set_schema_version(self, version: int):
        """Set schema version"""
        self.conn.execute('''
            INSERT INTO schema_info (version, description)
            VALUES (?, ?)
        ''', (version, f"Schema version {version}"))
    
    def _migrate_schema(self, from_version: int, to_version: int):
        """Migrate schema between versions"""
        logger.info(f"Migrating schema from {from_version} to {to_version}")
        
        # Migration logic would go here
        # For now, we'll just update the version
        self._set_schema_version(to_version)
    
    # Person management methods
    def add_person(self, name: str, notes: str = None) -> Optional[int]:
        """Add a new person"""
        if not self.connect():
            return None
        
        try:
            cursor = self.conn.execute('''
                INSERT INTO persons (name, notes, visit_count)
                VALUES (?, ?, 0)
            ''', (name, notes))
            
            person_id = cursor.lastrowid
            self.conn.commit()
            
            logger.info(f"Added person: {name} (ID: {person_id})")
            return person_id
            
        except Exception as e:
            logger.error(f"Failed to add person: {e}")
            self.conn.rollback()
            return None
        finally:
            self.disconnect()
    
    def get_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        """Get person by ID"""
        if not self.connect():
            return None
        
        try:
            cursor = self.conn.execute('''
                SELECT * FROM persons WHERE id = ?
            ''', (person_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get person: {e}")
            return None
        finally:
            self.disconnect()
    
    def get_all_persons(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all persons with pagination"""
        if not self.connect():
            return []
        
        try:
            cursor = self.conn.execute('''
                SELECT * FROM persons 
                WHERE enabled = TRUE
                ORDER BY last_seen DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get persons: {e}")
            return []
        finally:
            self.disconnect()
    
    def update_person_visit(self, person_id: int):
        """Update person's last visit"""
        if not self.connect():
            return False
        
        try:
            self.conn.execute('''
                UPDATE persons 
                SET last_seen = CURRENT_TIMESTAMP, visit_count = visit_count + 1
                WHERE id = ?
            ''', (person_id,))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update person visit: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()
    
    # Face embedding methods
    def add_face_embedding(self, person_id: int, embedding: bytes, image_path: str = None, quality_score: float = 0.0) -> Optional[int]:
        """Add face embedding for person"""
        if not self.connect():
            return None
        
        try:
            cursor = self.conn.execute('''
                INSERT INTO face_embeddings (person_id, embedding_data, image_path, quality_score)
                VALUES (?, ?, ?, ?)
            ''', (person_id, embedding, image_path, quality_score))
            
            embedding_id = cursor.lastrowid
            self.conn.commit()
            
            return embedding_id
            
        except Exception as e:
            logger.error(f"Failed to add face embedding: {e}")
            self.conn.rollback()
            return None
        finally:
            self.disconnect()
    
    def get_all_embeddings(self) -> List[Tuple[int, str, bytes]]:
        """Get all face embeddings"""
        if not self.connect():
            return []
        
        try:
            cursor = self.conn.execute('''
                SELECT fe.person_id, p.name, fe.embedding_data
                FROM face_embeddings fe
                JOIN persons p ON fe.person_id = p.id
                WHERE p.enabled = TRUE
            ''')
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            return []
        finally:
            self.disconnect()
    
    # Alert methods
    def add_alert(self, alert_type: str, person_id: int = None, message: str = None, 
                  severity: str = 'medium', image_path: str = None) -> Optional[int]:
        """Add system alert"""
        if not self.connect():
            return None
        
        try:
            cursor = self.conn.execute('''
                INSERT INTO alerts (person_id, alert_type, severity, message, image_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (person_id, alert_type, severity, message, image_path))
            
            alert_id = cursor.lastrowid
            self.conn.commit()
            
            return alert_id
            
        except Exception as e:
            logger.error(f"Failed to add alert: {e}")
            self.conn.rollback()
            return None
        finally:
            self.disconnect()
    
    def get_alerts(self, processed: bool = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get system alerts"""
        if not self.connect():
            return []
        
        try:
            sql = '''
                SELECT a.*, p.name as person_name
                FROM alerts a
                LEFT JOIN persons p ON a.person_id = p.id
            '''
            
            params = []
            if processed is not None:
                sql += ' WHERE a.processed = ?'
                params.append(processed)
            
            sql += ' ORDER BY a.timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor = self.conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
        finally:
            self.disconnect()
    
    # Visit tracking
    def record_visit(self, person_id: int = None, confidence: float = 0.0, 
                     camera_id: str = 'camera_0', image_path: str = None) -> Optional[int]:
        """Record a visit"""
        if not self.connect():
            return None
        
        try:
            cursor = self.conn.execute('''
                INSERT INTO visits (person_id, confidence, camera_id, image_path)
                VALUES (?, ?, ?, ?)
            ''', (person_id, confidence, camera_id, image_path))
            
            visit_id = cursor.lastrowid
            self.conn.commit()
            
            # Update person's visit count if known person
            if person_id:
                self.update_person_visit(person_id)
            
            return visit_id
            
        except Exception as e:
            logger.error(f"Failed to record visit: {e}")
            self.conn.rollback()
            return None
        finally:
            self.disconnect()
    
    # Configuration methods
    def get_config(self, key: str, default: str = None) -> str:
        """Get configuration value"""
        if not self.connect():
            return default
        
        try:
            cursor = self.conn.execute('SELECT value FROM configuration WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row[0] if row else default
            
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return default
        finally:
            self.disconnect()
    
    def set_config(self, key: str, value: str, description: str = None) -> bool:
        """Set configuration value"""
        if not self.connect():
            return False
        
        try:
            self.conn.execute('''
                INSERT OR REPLACE INTO configuration (key, value, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, value, description))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set config: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()
    
    # Analytics methods
    def get_visitor_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get visitor statistics"""
        if not self.connect():
            return {}
        
        try:
            stats = {}
            
            # Total visitors
            cursor = self.conn.execute('SELECT COUNT(*) FROM persons WHERE enabled = TRUE')
            stats['total_persons'] = cursor.fetchone()[0]
            
            # Recent visits
            cursor = self.conn.execute('''
                SELECT COUNT(*) FROM visits 
                WHERE timestamp >= datetime('now', '-{} days')
            '''.format(days))
            stats['recent_visits'] = cursor.fetchone()[0]
            
            # Unknown visitors
            cursor = self.conn.execute('''
                SELECT COUNT(*) FROM visits 
                WHERE person_id IS NULL AND timestamp >= datetime('now', '-{} days')
            '''.format(days))
            stats['unknown_visits'] = cursor.fetchone()[0]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get visitor stats: {e}")
            return {}
        finally:
            self.disconnect()
    
    def cleanup_old_data(self, retention_days: int = 30) -> int:
        """Clean up old data based on retention policy"""
        if not self.connect():
            return 0
        
        try:
            # Delete old visits
            cursor = self.conn.execute('''
                DELETE FROM visits 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(retention_days))
            
            deleted_visits = cursor.rowcount
            
            # Delete old processed alerts
            cursor = self.conn.execute('''
                DELETE FROM alerts 
                WHERE processed = TRUE AND processed_at < datetime('now', '-{} days')
            '''.format(retention_days))
            
            deleted_alerts = cursor.rowcount
            
            # Delete old system events
            cursor = self.conn.execute('''
                DELETE FROM system_events 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(retention_days))
            
            deleted_events = cursor.rowcount
            
            self.conn.commit()
            
            total_deleted = deleted_visits + deleted_alerts + deleted_events
            logger.info(f"Cleaned up {total_deleted} old records")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            self.conn.rollback()
            return 0
        finally:
            self.disconnect()

def main():
    """Demo/test function"""
    db = DatabaseManager()
    
    print("Initializing database...")
    if db.initialize_database():
        print("✓ Database initialized successfully")
        
        # Add test person
        person_id = db.add_person("Test Person", "Demo person")
        if person_id:
            print(f"✓ Added test person with ID: {person_id}")
            
            # Record test visit
            visit_id = db.record_visit(person_id, 0.95, "camera_0")
            if visit_id:
                print(f"✓ Recorded test visit with ID: {visit_id}")
            
            # Add test alert
            alert_id = db.add_alert("unknown_face", message="Test alert")
            if alert_id:
                print(f"✓ Added test alert with ID: {alert_id}")
        
        # Show stats
        stats = db.get_visitor_stats()
        print(f"✓ Visitor stats: {stats}")
        
    else:
        print("✗ Failed to initialize database")

if __name__ == "__main__":
    main()