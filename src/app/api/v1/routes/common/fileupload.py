# from flask import request, current_app
# from flask_restx import Resource, Namespace
# from flask_cors import cross_origin
# from src.app.api.v1.services.common.upload import FileUploadService
# from src.common.response_utils import (
#     success_response, error_response, internal_error_response
# )

# # Namespace
# file_upload_ns = Namespace("file", description="File upload operations", path="/api/v1")

# # Service instance
# file_upload_service = FileUploadService()


# # ---------------------------------------------------------------
# # Upload a file to AWS S3
# # ---------------------------------------------------------------
# @file_upload_ns.route('/upload')
# class FileUploadResource(Resource):
#     @cross_origin()
#     def options(self):
#         """Handle CORS preflight request"""
#         return '', 200

#     @file_upload_ns.doc('upload_file', params={
#         'folder': 'S3 folder name (balances, logos, profiles_pictures) - defaults to logos'
#     })
#     def post(self):
#         """
#         Upload a file to AWS S3 with folder selection.
#         ---
#         Request:
#           - multipart/form-data with 'file' field
#           - Query param 'folder': balances, logos, or profiles_pictures
#         Response:
#           - JSON with s3_filename and folder info
#         """
#         try:
#             if "file" not in request.files:
#                 return error_response(
#                     message="No file provided",
#                     status_code=400
#                 )

#             # Get folder parameter from query string
#             folder = request.args.get('folder', 'logos')
            
#             file = request.files["file"]
#             result, status_code = file_upload_service.upload(file, folder)
            
#             if status_code == 200:
#                 return success_response(
#                     message=result['message'],
#                     data=result['data'],
#                     status_code=status_code
#                 )
#             else:
#                 return error_response(
#                     message=result.get('message', 'Failed to upload file'),
#                     data=result,
#                     status_code=status_code
#                 )

#         except Exception as e:
#             return internal_error_response(
#                 message="Unexpected error while uploading file",
#                 error_details=str(e)
#             )

#     @file_upload_ns.doc('get_file_url')
#     @file_upload_ns.param('filename', 'The filename (S3 key) to get URL for')
#     def get(self):
#         """
#         Get S3 URL for a file by filename (S3 key).
#         ---
#         Query Parameters:
#           - filename: the S3 key of the file (e.g., "logos/abc123.jpg") (required)
#         Response:
#           - JSON with full S3 URL
#         """
#         filename = request.args.get('filename')
#         if not filename:
#             return error_response(
#                 message="Filename is required",
#                 status_code=400
#             )
        
#         try:
#             result, status_code = file_upload_service.get_url(filename)
            
#             if status_code == 200:
#                 return success_response(
#                     message=result['message'],
#                     data=result['data'],
#                     status_code=status_code
#                 )
#             else:
#                 return error_response(
#                     message=result.get('message', 'Failed to get file URL'),
#                     data=result,
#                     status_code=status_code
#                 )
                
#         except Exception as e:
#             return internal_error_response(
#                 message="Unexpected error while getting file URL",
#                 error_details=str(e)
#             )
