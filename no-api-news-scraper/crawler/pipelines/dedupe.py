import hashlib
def make_key(*parts): 
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
