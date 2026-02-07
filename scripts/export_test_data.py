#!/usr/bin/env python3
"""
Export test data from the database to JSON format for backup and analysis.
Usage:
    python scripts/export_test_data.py --format json --output test-data.json
    python scripts/export_test_data.py --format sql --output test-data.sql
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def export_to_json(connection_config: Dict[str, Any], output_file: str) -> None:
    """Export database tables to JSON format."""
    try:
        import pymysql
    except ImportError:
        print("Error: pymysql is required. Install with: pip install pymysql")
        sys.exit(1)

    tables = [
        'etl_tasks', 'etl_task_logs',
        'workflows', 'workflow_executions', 'workflow_schedules',
        'conversations',
        'knowledge_bases', 'indexed_documents',
        'data_assets', 'data_services', 'data_alerts',
        'metadata_databases', 'metadata_snapshots',
        'data_monitoring_rules', 'data_security_audit_logs'
    ]

    data = {}

    try:
        conn = pymysql.connect(
            host=connection_config.get('host', 'localhost'),
            port=connection_config.get('port', 3306),
            user=connection_config.get('user', 'onedata'),
            password=connection_config.get('password', ''),
            database=connection_config.get('database', 'onedata'),
            charset='utf8mb4'
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                if rows:
                    data[table] = rows
                    print(f"Exported {len(rows)} rows from {table}")
            except Exception as e:
                print(f"Warning: Could not export {table}: {e}")
                data[table] = []

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

    # Add metadata
    output_data = {
        'export_timestamp': None,  # Will be set when saved
        'database': connection_config.get('database', 'onedata'),
        'tables': data,
        'summary': {
            table: len(rows) for table, rows in data.items()
        }
    }

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, default=str)

    print(f"\nExport completed: {output_file}")
    print(f"Total tables: {len(data)}")
    print(f"Total rows: {sum(len(rows) for rows in data.values())}")


def export_to_sql(connection_config: Dict[str, Any], output_file: str) -> None:
    """Export database tables to SQL format using mysqldump."""
    import subprocess

    host = connection_config.get('host', 'localhost')
    port = connection_config.get('port', 3306)
    user = connection_config.get('user', 'onedata')
    password = connection_config.get('password', '')
    database = connection_config.get('database', 'onedata')

    tables = [
        'etl_tasks', 'etl_task_logs',
        'workflows', 'workflow_executions', 'workflow_schedules',
        'conversations',
        'knowledge_bases', 'indexed_documents',
        'data_assets', 'data_services', 'data_alerts',
        'metadata_databases', 'metadata_snapshots',
        'data_monitoring_rules', 'data_security_audit_logs'
    ]

    cmd = [
        'mysqldump',
        f'-h{host}',
        f'-P{port}',
        f'-u{user}',
        f'-p{password}',
        database
    ] + tables

    try:
        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"Warning: mysqldump returned code {result.returncode}")
                if result.stderr:
                    print(f"Error output: {result.stderr}")

        # Check file size
        file_size = os.path.getsize(output_file)
        print(f"SQL export completed: {output_file}")
        print(f"File size: {file_size} bytes")

    except FileNotFoundError:
        print("Error: mysqldump not found. Please ensure MySQL client is installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during SQL export: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Export test data from database')
    parser.add_argument(
        '--format',
        choices=['json', 'sql'],
        default='json',
        help='Export format (default: json)'
    )
    parser.add_argument(
        '--output', '-o',
        default='test-data-backup.json',
        help='Output file path (default: test-data-backup.json)'
    )
    parser.add_argument(
        '--host',
        default=os.getenv('MYSQL_HOST', 'localhost'),
        help='Database host'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('MYSQL_PORT', '3306')),
        help='Database port'
    )
    parser.add_argument(
        '--user',
        default=os.getenv('MYSQL_USER', 'onedata'),
        help='Database user'
    )
    parser.add_argument(
        '--password',
        default=os.getenv('MYSQL_PASSWORD', ''),
        help='Database password'
    )
    parser.add_argument(
        '--database',
        default=os.getenv('MYSQL_DATABASE', 'onedata'),
        help='Database name'
    )

    args = parser.parse_args()

    connection_config = {
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password,
        'database': args.database
    }

    if args.format == 'json':
        export_to_json(connection_config, args.output)
    else:
        export_to_sql(connection_config, args.output)


if __name__ == '__main__':
    main()
