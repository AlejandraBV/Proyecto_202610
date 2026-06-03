"""Folders API endpoints - organizar conversaciones por tema/asignatura"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Folder, Conversation
from app.schemas import FolderCreate, FolderUpdate, FolderResponse
from datetime import datetime

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=list[FolderResponse])
async def list_folders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all folders for the current user, ordered by creation date"""
    result = await db.execute(
        select(Folder)
        .where(Folder.user_id == current_user.id)
        .order_by(Folder.order, Folder.created_at)
    )
    folders = result.scalars().all()
    return folders


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new folder for organizing conversations"""
    # Check if folder with same name already exists
    result = await db.execute(
        select(Folder).where(
            (Folder.user_id == current_user.id) &
            (Folder.name == folder_data.name)
        )
    )
    existing = result.scalars().first()
    if existing:
        # Update color/icon of the existing folder instead of erroring
        if folder_data.color:
            existing.color = folder_data.color
        if folder_data.icon and folder_data.icon != "folder":
            existing.icon = folder_data.icon
        await db.commit()
        await db.refresh(existing)
        return existing
    
    # Create new folder
    folder = Folder(
        user_id=current_user.id,
        name=folder_data.name,
        description=folder_data.description,
        color=folder_data.color,
        icon=folder_data.icon,
        is_default=folder_data.is_default
    )
    
    # If this is the default, unset other defaults
    if folder_data.is_default:
        await db.execute(
            select(Folder).where(
                (Folder.user_id == current_user.id) &
                (Folder.is_default == True)
            )
        )
        default_folders = (await db.execute(
            select(Folder).where(
                (Folder.user_id == current_user.id) &
                (Folder.is_default == True)
            )
        )).scalars().all()
        for df in default_folders:
            df.is_default = False
    
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific folder by ID"""
    result = await db.execute(
        select(Folder).where(
            (Folder.id == folder_id) &
            (Folder.user_id == current_user.id)
        )
    )
    folder = result.scalars().first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    return folder


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    folder_data: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a folder"""
    result = await db.execute(
        select(Folder).where(
            (Folder.id == folder_id) &
            (Folder.user_id == current_user.id)
        )
    )
    folder = result.scalars().first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Update fields
    if folder_data.name:
        # Check if another folder has this name
        result = await db.execute(
            select(Folder).where(
                (Folder.user_id == current_user.id) &
                (Folder.name == folder_data.name) &
                (Folder.id != folder_id)
            )
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Folder '{folder_data.name}' already exists"
            )
        folder.name = folder_data.name
    
    if folder_data.description is not None:
        folder.description = folder_data.description
    if folder_data.color:
        folder.color = folder_data.color
    if folder_data.icon:
        folder.icon = folder_data.icon
    if folder_data.order is not None:
        folder.order = folder_data.order
    
    # Handle default folder
    if folder_data.is_default is not None:
        if folder_data.is_default:
            # Unset other defaults
            default_folders = (await db.execute(
                select(Folder).where(
                    (Folder.user_id == current_user.id) &
                    (Folder.is_default == True) &
                    (Folder.id != folder_id)
                )
            )).scalars().all()
            for df in default_folders:
                df.is_default = False
        folder.is_default = folder_data.is_default
    
    folder.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(folder)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a folder and move its conversations to default folder"""
    result = await db.execute(
        select(Folder).where(
            (Folder.id == folder_id) &
            (Folder.user_id == current_user.id)
        )
    )
    folder = result.scalars().first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Move conversations to default folder if one exists
    default_folder = (await db.execute(
        select(Folder).where(
            (Folder.user_id == current_user.id) &
            (Folder.is_default == True)
        )
    )).scalars().first()
    
    if default_folder:
        # Move all conversations to default folder
        await db.execute(
            select(Conversation).where(Conversation.folder_id == folder_id)
        )
        conversations = (await db.execute(
            select(Conversation).where(Conversation.folder_id == folder_id)
        )).scalars().all()
        for conv in conversations:
            conv.folder_id = default_folder.id
    else:
        # No default folder, just clear folder_id
        await db.execute(
            select(Conversation).where(Conversation.folder_id == folder_id)
        )
        conversations = (await db.execute(
            select(Conversation).where(Conversation.folder_id == folder_id)
        )).scalars().all()
        for conv in conversations:
            conv.folder_id = None
    
    # Delete the folder
    await db.delete(folder)
    await db.commit()


@router.get("/{folder_id}/conversations")
async def get_folder_conversations(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all conversations in a folder"""
    # Verify folder belongs to user
    result = await db.execute(
        select(Folder).where(
            (Folder.id == folder_id) &
            (Folder.user_id == current_user.id)
        )
    )
    folder = result.scalars().first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Get conversations
    result = await db.execute(
        select(Conversation)
        .where(Conversation.folder_id == folder_id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    
    return {
        "folder": folder,
        "conversations": conversations,
        "count": len(conversations)
    }
