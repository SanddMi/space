$(document).ready(function() {
    const dropZone = $('#messages');
    const dropZoneOverlay = $('#dropZoneOverlay');
    const fileInput = $('#videoFile');
    let isDraggingFile = false;
    let isSelectingText = false;

    $(document).on('dragstart', '#profile-pic, .message-profile-pic, .action-icon', function(e) {
        e.preventDefault();
        return false;
    });

    $(document)
        .on('mousedown', function(e) {
            const $target = $(e.target);
            isSelectingText = $target.is('input, textarea, [contenteditable="true"]') || 
                            window.getSelection().toString().length > 0;
        })
        .on('mouseup', function() {
            setTimeout(() => {
                isSelectingText = window.getSelection().toString().length > 0;
            }, 50);
        });

    $(document).on('dragend', function() {
        isDraggingFile = false;
    });

    $(document).on('dragenter', function(e) {
        if ($(e.target).hasClass('message-profile-pic')) {
            isDraggingFile = false;
            return;
        }

        const dt = e.originalEvent.dataTransfer;
        isDraggingFile = dt && Array.from(dt.types).includes('Files');

        if (!isDraggingFile || isSelectingText) return;
        e.preventDefault();
        dropZoneOverlay.removeClass('hidden');
    });
    
    $(document).on('dragleave', function(e) {
        if (!isDraggingFile || isSelectingText) return;
        if (e.originalEvent.clientX <= 0 || 
            e.originalEvent.clientY <= 0 || 
            e.originalEvent.clientX >= $(window).width() || 
            e.originalEvent.clientY >= $(window).height()) {
            dropZoneOverlay.addClass('hidden');
        }
    });
    
    $(document).on('drop', function(e) {
        if (!isDraggingFile || isSelectingText) {
            isSelectingText = false;
            return;
        }

        e.preventDefault();
        e.stopPropagation();
        dropZoneOverlay.addClass('hidden');
        
        if (e.originalEvent.dataTransfer.files.length) {
            const file = e.originalEvent.dataTransfer.files[0];
            handleDroppedFile(file);
        }
    });
    
    $(document).on('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    });
    
    function handleDroppedFile(file) {
        $("#mediaPreview").empty();
        
        if (file.type.startsWith('image/') || 
            file.type.startsWith('video/') || 
            file.name.endsWith('.rar')) {
            
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput[0].files = dataTransfer.files;
            
            // Show preview
            showMediaPreview(file);
        } else {
            alert('Unsupported file type. Please upload images, videos, or RAR files.');
        }
    }
});