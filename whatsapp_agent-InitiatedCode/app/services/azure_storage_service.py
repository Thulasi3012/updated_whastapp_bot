# app/services/azure_storage_service.py

import os
import logging
from typing import List, Dict, Any, Optional, BinaryIO, Union
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import tempfile
from app.config import settings

logger = logging.getLogger(__name__)

class AzureStorageService:
    def __init__(self):
        self.account_name = settings.AZURE_STORAGE_ACCOUNT_NAME
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = settings.AZURE_DATA_CONTAINER
        
        # For logging/debugging
        logger.info(f"Initializing AzureStorageService with account: {self.account_name}")
        logger.info(f"Container name: {self.container_name}")
        
        self.client = self._initialize_blob_client()
        self.container_client = self._get_container_client()

    def _initialize_blob_client(self) -> BlobServiceClient:
        """Initialize the Azure Blob Storage client"""
        try:
            if not self.connection_string:
                raise ValueError("Azure Storage connection string not provided")
            
            # Initialize with connection string
            blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            
            # Test the connection (with error handling)
            try:
                blob_service_client.get_account_information()
                logger.info("Successfully connected to Azure Blob Storage")
            except Exception as e:
                logger.warning(f"Connection test failed, but continuing: {e}")
                # Continue anyway - we'll validate access when needed
                
            return blob_service_client
            
        except Exception as e:
            logger.error(f"Error initializing Azure Blob Storage client: {e}")
            # Create a fallback client that will log errors but not crash
            raise
    def get_file(self, file_path: str) -> Optional[bytes]:
        """Get blob content from the container with improved error handling"""
        try:
            logger.info(f"Attempting to get blob from path: {file_path}")
            
            try:
                blob_client = self.container_client.get_blob_client(file_path)
                
                if not blob_client.exists():
                    logger.info(f"Blob not found at path: {file_path}")
                    return None
                    
                blob_data = blob_client.download_blob()
                return blob_data.readall()
            except Exception as e:
                logger.error(f"Error getting blob {file_path}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Critical error accessing storage: {e}")
            return None

    def _get_container_client(self) -> ContainerClient:
        """Get the Azure Blob Storage container client"""
        try:
            container_client = self.client.get_container_client(self.container_name)
            
            # Create container if it doesn't exist
            try:
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
            except ResourceExistsError:
                logger.info(f"Container already exists: {self.container_name}")
            
            return container_client
            
        except Exception as e:
            logger.error(f"Error getting container client: {e}")
            raise
    
    def _get_project_folder(self, project_id: str) -> str:
        """Get the folder name for a project in Azure Blob Storage"""
        # Map project ID to folder name using the PROJECT_FOLDER_MAP
        folder_name = settings.PROJECT_FOLDER_MAP.get(project_id, project_id)
        return folder_name
            
    def list_files(self, prefix: str = None) -> List[Dict[str, Any]]:
        """
        List blobs in the container with the given prefix
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of dictionaries with blob information
        """
        try:
            blob_list = self.container_client.list_blobs(name_starts_with=prefix)
            return [
                {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None
                }
                for blob in blob_list
            ]
        except Exception as e:
            logger.error(f"Error listing blobs: {e}")
            return []

    def get_file(self, file_path: str) -> Optional[bytes]:
        """Get blob content from the container"""
        try:
            logger.info(f"Attempting to get blob from path: {file_path}")
            
            blob_client = self.container_client.get_blob_client(file_path)
            
            if not blob_client.exists():
                logger.info(f"Blob not found at path: {file_path}")
                return None
                
            blob_data = blob_client.download_blob()
            return blob_data.readall()
            
        except ResourceNotFoundError:
            logger.info(f"Blob not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error getting blob {file_path}: {e}")
            return None
    
    def upload_file(self, file_path: str, content: Union[BinaryIO, bytes], content_type: str = None, overwrite: bool = True) -> bool:
        """
        Upload file to the container
        
        Args:
            file_path: Path to save the blob in the container
            content: File content (file-like object or bytes)
            content_type: Optional content type
            overwrite: Whether to overwrite existing blob
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            
            # Handle different content types
            if hasattr(content, 'read'):
                # It's a file-like object
                content_data = content.read()
            else:
                # It's already bytes
                content_data = content
            
            blob_client.upload_blob(
                content_data, 
                content_type=content_type,
                overwrite=overwrite
            )
            
            logger.info(f"Successfully uploaded blob: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading blob {file_path}: {e}")
            return False
            
    def upload_from_string(self, file_path: str, content: str, content_type: str = None, overwrite: bool = True) -> bool:
        """
        Upload string content to the container
        
        Args:
            file_path: Path to save the blob in the container
            content: String content
            content_type: Optional content type
            overwrite: Whether to overwrite existing blob
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            blob_client.upload_blob(
                content, 
                content_type=content_type or "text/plain",
                overwrite=overwrite
            )
            
            logger.info(f"Successfully uploaded string to blob: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading string to blob {file_path}: {e}")
            return False
            
    def get_project_files(self, project_id: str, file_type: str = None) -> List[Dict[str, Any]]:
        """
        Get blobs for a specific project
        
        Args:
            project_id: The project ID (from database)
            file_type: Optional file type (brochures, videos, transcripts, etc.)
            
        Returns:
            List of dictionaries with blob information
        """
        try:
            # Get the folder name for this project
            project_folder = self._get_project_folder(project_id)
            
            # Build the prefix based on project and file type
            prefix = f"{settings.STORAGE_FOLDER_PREFIX}{project_folder}"
            if file_type:
                prefix = f"{prefix}/{file_type}/"
                
            return self.list_files(prefix)
            
        except Exception as e:
            logger.error(f"Error getting project files: {e}")
            return []
            
    def get_transcript_content(self, project_id: str, filename: str) -> Optional[str]:
        """
        Get transcript content for a specific file
        
        Args:
            project_id: The project ID (from database)
            filename: The transcript filename
            
        Returns:
            Transcript content as string, or None if blob not found
        """
        try:
            # Get the folder name for this project
            project_folder = self._get_project_folder(project_id)
            
            file_path = f"{settings.STORAGE_FOLDER_PREFIX}{project_folder}/transcripts/{filename}"
            content = self.get_file(file_path)
            if content:
                return content.decode('utf-8')
            return None
            
        except Exception as e:
            logger.error(f"Error getting transcript content: {e}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a blob from the container
        
        Args:
            file_path: Path to the blob to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            blob_client.delete_blob()
            logger.info(f"Successfully deleted blob: {file_path}")
            return True
            
        except ResourceNotFoundError:
            logger.info(f"Blob not found for deletion: {file_path}")
            return True  # Consider it successful if it doesn't exist
        except Exception as e:
            logger.error(f"Error deleting blob {file_path}: {e}")
            return False
    
    def get_blob_url(self, file_path: str) -> str:
        """
        Get the URL for a blob
        
        Args:
            file_path: Path to the blob
            
        Returns:
            The blob URL
        """
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            return blob_client.url
        except Exception as e:
            logger.error(f"Error getting blob URL: {e}")
            return ""
    
    def generate_download_url(self, file_path: str) -> str:
        """
        Generate a download URL for a blob
        
        Args:
            file_path: Path to the blob
            
        Returns:
            Download URL (in this case, just the blob URL since we're not using SAS tokens)
        """
        return self.get_blob_url(file_path)