import re
from typing import Tuple, List

# Regex patterns for high-signal debugging tokens
HEX_CODE_PATTERN = re.compile(r'\b0x[0-9a-fA-F]{4,8}\b')
EXIT_CODE_PATTERN = re.compile(r'\b(?:exit\s+code|code)\s*[:=]?\s*(\d{1,4})\b', re.IGNORECASE)
HTTP_CODE_PATTERN = re.compile(r'\b(?:HTTP|status)\s*[:=]?\s*([45]\d{2})\b', re.IGNORECASE)
SIGNAL_PATTERN = re.compile(r'\b(SIG[A-Z]{3,6})\b')
SQLSTATE_PATTERN = re.compile(r'\b(?:SQLSTATE|SQL State)\s*[:=]?\s*([0-9A-Z]{5})\b', re.IGNORECASE)
EXCEPTION_PATTERN = re.compile(
    r'\b([A-Z][a-zA-Z0-9]*(?:Error|Exception|Fault|Crash|Timeout|Failure|Refused))\b'
)
COMMON_KEYWORDS = re.compile(
    r'\b(CrashLoopBackOff|OOMKilled|ECONNREFUSED|EACCES|ENOENT|EPERM|deadlock|Access Denied|File Not Found|Connection Refused)\b',
    re.IGNORECASE
)

# Noise cleanup patterns
TIMESTAMP_PATTERN = re.compile(r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b')
FILE_PATH_PATTERN = re.compile(r'(?:[A-Za-z]:\\(?:[^\s\\/:*?"<>|\r\n]+\\)*[^\s\\/:*?"<>|\r\n]+)|(?:/(?:[^\s/]+/)+[^\s/]+)')
HEX_MEM_ADDR = re.compile(r'\b0x[0-9a-fA-F]{8,16}\b')

class QueryRewriter:
    @staticmethod
    def extract_error_signals(raw_text: str) -> Tuple[List[str], str]:
        """
        Extracts specific error codes and produces a cleaned search intent string.
        Returns: (extracted_codes, clean_search_intent)
        """
        codes: List[str] = []
        
        # 1. Hex codes (e.g. 0x80070005)
        for match in HEX_CODE_PATTERN.finditer(raw_text):
            code = match.group(0).lower()
            if code not in codes:
                codes.append(code)
                
        # 2. Exit codes (e.g. exit code 137)
        for match in EXIT_CODE_PATTERN.finditer(raw_text):
            val = f"exit code {match.group(1)}"
            if val not in codes:
                codes.append(val)
                
        # 3. HTTP status codes (e.g. 502, 504)
        for match in HTTP_CODE_PATTERN.finditer(raw_text):
            val = f"HTTP {match.group(1)}"
            if val not in codes:
                codes.append(val)
                
        # 4. Signals (e.g. SIGKILL, SIGSEGV)
        for match in SIGNAL_PATTERN.finditer(raw_text):
            val = match.group(1)
            if val not in codes:
                codes.append(val)
                
        # 5. SQLSTATE (e.g. 53300, 40P01)
        for match in SQLSTATE_PATTERN.finditer(raw_text):
            val = f"SQLSTATE {match.group(1)}"
            if val not in codes:
                codes.append(val)
                
        # 6. Exception classes (e.g. RecursionError, OperationalError)
        for match in EXCEPTION_PATTERN.finditer(raw_text):
            val = match.group(1)
            if val not in codes and len(val) > 4:
                codes.append(val)
                
        # 7. Common technical error keywords
        for match in COMMON_KEYWORDS.finditer(raw_text):
            val = match.group(1)
            if val not in codes:
                codes.append(val)

        # Build clean search intent:
        # Strip timestamps, long memory addresses, verbose file paths
        clean_text = TIMESTAMP_PATTERN.sub('', raw_text)
        clean_text = HEX_MEM_ADDR.sub('', clean_text)
        clean_text = FILE_PATH_PATTERN.sub('', clean_text)
        
        # Keep high-information lines (e.g. lines with error, failed, denied, exception)
        lines = clean_text.splitlines()
        informative_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if any(k in line_str.lower() for k in [
                'error', 'fail', 'denied', 'exception', 'refused', 'killed', 'fatal',
                'deadlock', 'crash', 'warn', 'timeout', 'cannot find',
                'started before', 'before ready', 'ready', 'startup', 'docker', 'container',
                'race condition', 'boot', 'init', 'connect'
            ]):
                informative_lines.append(line_str)
                
        if not informative_lines:
            informative_lines = [l.strip() for l in lines[:3] if l.strip()]

        condensed_text = " ".join(informative_lines)
        # Clean extra whitespaces and punctuation
        condensed_text = re.sub(r'[\t\r\n]+', ' ', condensed_text)
        condensed_text = re.sub(r'\s{2,}', ' ', condensed_text).strip()
        
        # Prepend extracted prominent codes for BM25 and vector emphasis
        codes_prefix = " ".join(codes[:4])
        search_intent = f"{codes_prefix} {condensed_text}".strip()
        
        # Limit intent string length
        if len(search_intent) > 300:
            search_intent = search_intent[:300]
            
        return codes, search_intent or raw_text[:200]
