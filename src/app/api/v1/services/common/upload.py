# import boto3
# import hashlib
# from flask import current_app, make_response,Response
# from werkzeug.utils import secure_filename
# from botocore.exceptions import ClientError

# class FileUploadService:
#     """
#     Service: Handles uploads to AWS S3 using content hash as filename.
#     """

#     def upload(self, file, folder="logos"):
#         """
#         Uploads the provided file to the specified S3 folder.
#         Uses the content hash for deduplication.
        
#         Args:
#             file: File object from request
#             folder: S3 folder name (balances, logos, profiles_pictures)
#         """
#         # Basic validation
#         if not file or not file.filename:
#             return {"success": False, "message": "File is required"}, 400

#         # Validate folder parameter
#         valid_folders = ["balances", "logos", "profiles_pictures"]
#         if folder not in valid_folders:
#             return {"success": False, "message": f"Invalid folder. Must be one of: {', '.join(valid_folders)}"}, 400

#         try:
#             # Read file and compute hash for deduplication
#             file_bytes = file.read()
#             file_hash = hashlib.md5(file_bytes).hexdigest()
#             file.seek(0)  # Reset pointer after reading

#             # Filename setup
#             filename = secure_filename(file.filename)
#             extension = filename.rsplit('.', 1)[-1] if '.' in filename else ''
#             s3_prefix = f"{folder}/"  # Dynamic folder based on input
#             s3_filename = f"{s3_prefix}{file_hash}.{extension}" if extension else f"{s3_prefix}{file_hash}"

#             # S3 Config
#             s3 = boto3.client(
#                 "s3",
#                 aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
#                 aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
#                 region_name=current_app.config["AWS_REGION"]
#             )
#             bucket_name = current_app.config["AWS_S3_BUCKET_NAME"]

#             # S3 Deduplication Logic
#             try:
#                 s3.head_object(Bucket=bucket_name, Key=s3_filename)
#                 current_app.logger.info(f"Duplicate file found on S3: {s3_filename}")
#             except ClientError as e:
#                 if e.response.get("Error", {}).get("Code", "") == "404":
#                     try:
#                         s3.upload_fileobj(
#                             file,
#                             Bucket=bucket_name,
#                             Key=s3_filename,
#                             ExtraArgs={"ContentType": file.content_type}
#                         )
#                     except ClientError as ce:
#                         current_app.logger.error(f"S3 Upload Error: {ce}")
#                         return {"success": False, "message": "Failed to upload file to S3", "error": str(ce)}, 500
#                     except Exception as ex:
#                         current_app.logger.error(f"Unexpected Upload Error: {ex}")
#                         return {"success": False, "message": "Unexpected error during file upload", "error": str(ex)}, 500
#                 else:
#                     current_app.logger.error(f"S3 file check error: {e}")
#                     return {"success": False, "message": "Error verifying S3 file", "error": str(e)}, 500

#             return {
#                 "success": True,
#                 "message": "File uploaded successfully",
#                 "data": {
#                     "s3_filename": s3_filename,
#                     "folder": folder
#                 }
#             }, 200

#         except Exception as e:
#             current_app.logger.error(f"Unexpected error while uploading file: {str(e)}")
#             # More user-friendly error message for endpoint error
#             if "Could not connect to the endpoint URL" in str(e):
#                 return {
#                     "success": False,
#                     "message": "Could not connect to AWS S3 (endpoint unreachable). Please check your network and S3 configuration.",
#                     "error": str(e)
#                 }, 500
#             return {
#                 "success": False,
#                 "message": "Unexpected error while uploading file",
#                 "error": str(e)
#             }, 500

#     def get_url(self, filename):
#         """
#         Get the full S3 URL for a given filename.
        
#         Args:
#             filename: S3 key/filename (e.g., "logos/abc123.jpg")
            
#         Returns:
#             dict: Response with S3 URL or error
#         """
#         try:
#             bucket_name = current_app.config['AWS_S3_BUCKET_NAME']
#             region = current_app.config['AWS_REGION']
            
#             # Construct S3 URL
#             s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{filename}"
            
#             return {
#                 "success": True,
#                 "message": "File URL generated successfully",
#                 "data": {
#                     "s3_url": s3_url,
#                     "filename": filename
#                 }
#             }, 200
            
#         except Exception as e:
#             current_app.logger.error(f"Error generating S3 URL: {str(e)}")
#             return {
#                 "success": False,
#                 "message": "Error generating file URL",
#                 "error": str(e)
#             }, 500

#     def get(self, file):
#         """
#         Get file content from S3 (for direct file serving).
        
#         Args:
#             file: S3 key/filename
            
#         Returns:
#             Response: File response or error
#         """
#         try:
#             bucket_name = current_app.config['AWS_S3_BUCKET_NAME']
#             region = current_app.config['AWS_REGION']

#             s3 = boto3.client(
#                 's3',
#                 aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
#                 aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
#                 region_name=region
#             )

#             # Get object from S3
#             s3_object = s3.get_object(Bucket=bucket_name, Key=file)
#             image_data = s3_object['Body'].read()
#             content_type = s3_object['ContentType']

#             return Response(image_data, mimetype=content_type)

#         except ClientError as e:
#             if e.response['Error']['Code'] in ['NoSuchKey', '404']:
#                 return make_response({"success": False, "message": "File not found"}, 404)
#             current_app.logger.error(f"S3 ClientError in get_file: {e}")
#             return make_response({"success": False, "message": "S3 error", "error": str(e)}, 500)
#         except Exception as e:
#             current_app.logger.error(f"Exception in get_file: {e}")
#             return make_response({"success": False, "message": "Server error", "error": str(e)}, 500)