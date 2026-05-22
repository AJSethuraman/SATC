def get_column_letter(n):
    s=''
    while n:
        n,r=divmod(n-1,26); s=chr(65+r)+s
    return s
