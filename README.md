# File Organizer (Python)

An automation tool built with Python that organizes files into structured folders based on file type, improving file management efficiency.

## 🚀 Overview
Manually sorting files can be time-consuming and inefficient. This project automates the process by scanning a directory and organizing files into categorized folders such as Images, Videos, Documents, and more.

## ✨ Key Features
- Automatically categorizes files by extension
- Creates folders dynamically if they do not exist
- Supports multiple file types:
  - Images (.jpg, .png, .gif, etc.)
  - Videos (.mp4, .mov, etc.)
  - Documents (.pdf, .docx, etc.)
  - Music, Archives, Code, and more
- Handles uncategorized files by placing them in an "Other" folder

## 🛠️ Technical Details
- Built using Python 3
- Utilizes `os` for directory and file management
- Uses `shutil` for file movement and organization
- Designed to work across any user-specified directory

## ▶️ Getting Started

### 1. Clone the repository


### 2. Navigate into the project directory


### 3. Run the script


### 4. Enter the target folder path
Example: 
-/users/yourname/downloads

## 📂 Example

**Before:**
-downloads/
-image.png
-resume.pdf
-video.mp4


**After:**
-downloads
-images/
-images.png
-documents/
resume.pdf
videos/
video.mp4



## 📈 Impact
This tool reduces manual file organization time and provides a scalable way to maintain clean and structured directories.

## 🔮 Future Enhancements
- Automatic execution without user input
- Scheduled organization (daily/weekly)
- GUI-based interface
- Duplicate file handling
- Logging system for tracking file movements

## 👨‍💻 Author
Jerome
