"""In chuỗi băm của một mật khẩu, để thêm tài khoản vào seed.sql.

Chạy:  python tao_mat_khau.py <mật khẩu>
"""
import hashlib
import sys

print(hashlib.sha256(sys.argv[1].encode()).hexdigest())
