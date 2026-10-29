
import gzip

# Read the binary file
with open('./a1661812', 'rb') as f:
    # Decompress the content
    decompressed_data = gzip.decompress(f.read())

# The result is bytes. If the original content was text/PHP serialization:
try:
    content = decompressed_data.decode('utf-8')
    print(content)
    
    # IF the content inside turns out to be PHP serialized data:
    # You can now pass 'content' to your PHP unserialize logic or python phpserialize
except UnicodeDecodeError:
    # If it's not text, save it as a file
    with open('output_file', 'wb') as out:
        out.write(decompressed_data)   
