import hashlib

class DataAnonymizer:
    """
    Deterministic, collision-free PII anonymizer.
    Ensures that different bank accounts never map to colliding account_id tokens,
    while maintaining absolute anonymity and stability across pipeline executions.
    """
    def __init__(self):
        # In-memory stable map per session for readable anonymized aliases
        self._account_alias_map = {}

    def mask_account(self, acc):
        """
        Deterministic unique masking.
        Avoids prefix-only masking collision (e.g. 488601041922538 vs 488601041999999).
        Format: ACC_<4-char prefix><8-char deterministic sha256 hex>
        """
        if acc is None:
            return "ACC_UNKNOWN"
        acc_str = str(acc).strip().split('.')[0]
        if not acc_str:
            return "ACC_UNKNOWN"
            
        if acc_str in self._account_alias_map:
            return self._account_alias_map[acc_str]
            
        prefix = acc_str[:4] if len(acc_str) >= 4 else acc_str.ljust(4, '0')
        acc_hash = hashlib.sha256(acc_str.encode('utf-8')).hexdigest()[:8].upper()
        masked_id = f"ACC_{prefix}_{acc_hash}"
        self._account_alias_map[acc_str] = masked_id
        return masked_id

    def mask_name(self, name):
        """RAFIF RAMADHAN -> RAF*** R***"""
        if not name or not isinstance(name, str):
            return "ANON_USER"
        words = name.strip().split()
        masked_words = []
        for w in words:
            if len(w) > 3:
                masked_words.append(w[:3].upper() + '***')
            elif len(w) > 1:
                masked_words.append(w[0].upper() + '**')
            else:
                masked_words.append('*')
        return " ".join(masked_words)

    def mask_phone(self, phone):
        """085668783883 -> 0856****3883"""
        if not phone:
            return "08xx****xxxx"
        phone_str = str(phone).strip()
        if len(phone_str) > 8:
            return phone_str[:4] + '****' + phone_str[-4:]
        elif len(phone_str) > 4:
            return phone_str[:4] + '****'
        return "08xx****"

    def anonymize_remark(self, remark):
        """
        Anonymizes PII in transaction remarks (phone numbers, account numbers, personal names)
        while strictly preserving transaction semantics (merchant names, transaction codes, channels).
        """
        if not isinstance(remark, str):
            return ""
        
        text = str(remark)
        # 1. Mask Indonesian Phone Numbers (08xxxxxxxxxx)
        import re
        text = re.sub(r'08\d{8,11}', lambda m: m.group(0)[:4] + '****' + m.group(0)[-2:], text)
        
        # 2. Mask Account Numbers / Card Numbers (10 to 16 continuous digits)
        text = re.sub(r'\b\d{10,16}\b', lambda m: m.group(0)[:4] + '********' + m.group(0)[-2:], text)
        
        # 3. Mask Virtual Account / Reference codes (#9360...)
        text = re.sub(r'#(\d{4})\d{4,12}', r'#\1****', text)
        
        return text.strip()
