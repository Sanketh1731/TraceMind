import pytest
from app.services.query_rewriter import QueryRewriter

def test_extract_hex_and_permission():
    raw_log = "2026-09-05 22:45:10 Error: 0x80070005 Access Denied while installing package at C:\\Users\\HP\\AppData\\Local\\Temp\\setup.msi"
    codes, intent = QueryRewriter.extract_error_signals(raw_log)
    
    assert "0x80070005" in codes
    assert "Access Denied" in codes
    assert "0x80070005" in intent
    # Ensure local path and timestamp are stripped from intent
    assert "2026-09-05" not in intent
    assert "C:\\Users\\HP" not in intent

def test_extract_exit_code_and_oom():
    raw_log = "Error: container api-gateway-7f8d6 was killed (exit code 137): OOMKilled by cgroup killer"
    codes, intent = QueryRewriter.extract_error_signals(raw_log)
    
    assert "exit code 137" in codes
    assert "OOMKilled" in codes
    assert "oomkilled" in intent.lower()

def test_extract_econnrefused():
    raw_log = """
    Error: connect ECONNREFUSED 127.0.0.1:5432
        at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1494:16)
        errno: -4078, code: 'ECONNREFUSED', syscall: 'connect'
    """
    codes, intent = QueryRewriter.extract_error_signals(raw_log)
    
    assert "ECONNREFUSED" in codes
    assert "econnrefused" in intent.lower()

def test_extract_sqlstate():
    raw_log = "psycopg2.OperationalError: FATAL: sorry, too many clients already (SQLSTATE 53300)"
    codes, intent = QueryRewriter.extract_error_signals(raw_log)
    
    assert "SQLSTATE 53300" in codes
    assert "OperationalError" in codes
