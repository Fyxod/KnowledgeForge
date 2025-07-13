# Testing Script for Bug Fixes

## Issues to Test

### Issue 1: File Upload Always Creates New Thread
**Problem**: When uploading files to an existing thread with messages, a new thread is created instead of adding files to the current thread.

**Expected Behavior**: Files should be added to the current thread if one is selected.

**Test Steps**:
1. Login to the application
2. Click "New Chat" button to create an empty thread
3. Send a text message to the AI
4. Upload a file using the file upload button
5. **Expected**: File should be added to the same thread
6. **Bug**: New thread is created

### Issue 2: "New Chat" Button Not Working
**Problem**: The "New Chat" button doesn't create a new thread.

**Expected Behavior**: Clicking "New Chat" should create a new empty thread and select it.

**Test Steps**:
1. Login to the application
2. Click "New Chat" button in sidebar
3. **Expected**: New thread appears in sidebar and is selected
4. **Bug**: Nothing happens or errors occur

## Test Execution

### Test Environment Setup
1. Backend running on http://localhost:8000
2. Frontend running on http://localhost:5173
3. Browser developer tools open to monitor console logs

### Test Case 1: New Chat Button
1. Open browser to http://localhost:5173
2. Login with test credentials
3. Open browser console to monitor logs
4. Click "New Chat" button
5. **Check**: Console shows "handleCreateThread called"
6. **Check**: Console shows "New thread created:" with response
7. **Check**: Console shows "Selecting new thread:" with thread ID
8. **Check**: New thread appears in sidebar
9. **Check**: Thread is selected (highlighted)
10. **Check**: Chat area shows empty thread state

### Test Case 2: File Upload to New Thread
1. Ensure no thread is selected (welcome screen visible)
2. Upload a file using drag-and-drop or click
3. **Check**: Console shows upload request with threadId: null
4. **Check**: Console shows new thread creation
5. **Check**: File upload completes successfully
6. **Check**: New thread appears in sidebar with document icon
7. **Check**: Thread is automatically selected

### Test Case 3: File Upload to Existing Thread (The Main Bug)
1. Click "New Chat" to create empty thread
2. Send a text message: "Hello AI"
3. Wait for AI response
4. Note the thread ID in console/sidebar
5. Upload a file to this thread
6. **Check**: Console shows upload request with correct threadId
7. **Check**: Console shows "Files added to existing thread"
8. **Check**: File appears in the SAME thread (not new thread)
9. **Check**: Thread in sidebar shows document icon
10. **Check**: No new thread is created

### Test Case 4: Multiple File Uploads to Same Thread
1. Create thread and add first file (from Test Case 3)
2. Send another message
3. Upload a second file
4. **Check**: Second file goes to same thread
5. **Check**: No additional threads created
6. **Check**: Thread shows multiple documents

## Debugging Information

### Console Logs to Monitor
- `handleCreateThread called`
- `New thread created:` + response object
- `handleFileUpload called:` + request details
- `Upload request:` + formData details
- `Upload response:` + server response
- `Selecting new thread:` + thread ID
- `Files added to existing thread:` + thread ID

### Backend Logs to Monitor
- `Thread name:` + thread name
- `Thread ID:` + thread ID
- `Creating a new thread` or `Updating existing thread`
- `Thread [id] not found for user` (error case)
- `Available threads:` + thread list

### UI Elements to Verify
- "New Chat" button shows loading spinner when clicked
- New threads appear in sidebar immediately
- Selected thread is highlighted
- Document icons appear for threads with files
- Welcome screen disappears when thread selected
- File upload shows progress indicator
- Error messages display if something fails

## Expected Results After Fixes

1. **New Chat Button**: Creates empty thread, appears in sidebar, gets selected
2. **File Upload to No Thread**: Creates new thread with files
3. **File Upload to Existing Thread**: Adds files to current thread, no new thread created
4. **Multiple Uploads**: All go to same thread if thread is selected
5. **Thread Switching**: Can switch between threads with their respective content
6. **UI Feedback**: Proper loading states and error handling

## If Tests Fail

### New Chat Not Working
- Check backend logs for thread creation endpoint
- Verify authentication is working
- Check network tab for API requests
- Verify thread appears in database

### File Upload Creating New Threads
- Check if threadId is being passed correctly in formData
- Verify backend receives threadId parameter
- Check if thread exists validation is working
- Monitor backend logs for thread lookup

### General Debugging
- Clear browser cache and localStorage
- Restart backend server
- Check for JavaScript errors in console
- Verify API endpoints are accessible
- Test with different file types and sizes
