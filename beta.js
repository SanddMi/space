<script>
    // Add this at the top with other variables
    let currentReplyMessageId = null;
    let currentReplyText = '';

    // Modify the reply menu item click handler
    $(document).on('click', '.menu-item', function() {
        const action = $(this).text();
        const targetElem = $('.context-menu').data('target');
        const msgId = $(targetElem).data('message-id');

        if (action == "Delete Message" && msgId !== undefined) {
            socket.emit('delete_message', msgId);
        } else if (action === 'Copy Text') {
            const getText = $(targetElem).find('.message-text').text().trim();
            copyText(getText);
        } else if (action == 'Edit Message' && msgId !== undefined) {
            // ... existing edit code ...
        } else if (action == "Reply" && msgId !== undefined) {
            currentReplyMessageId = msgId;
            currentReplyText = $(targetElem).find('.message-text').text().trim();
            
            $('#replyPreview').remove();
            $('#chatContainer').append(`
                <div id='replyPreview'>
                    <strong>Replying to:</strong> ${currentReplyText}
                    <span class="cancel-reply" style="cursor:pointer; margin-left:10px; color:#dc3545">✕</span>
                </div>
            `);
            
            // Focus the input but preserve any existing text
            $('#userInput').focus();
        }
    });

    // Add click handler for cancel reply
    $(document).on('click', '.cancel-reply', function() {
        $('#replyPreview').remove();
        currentReplyMessageId = null;
        currentReplyText = '';
    });

    // Modify the sendText function to handle replies
    async function sendText() {
        const textInput = document.getElementById('userInput');
        const fileInput = document.getElementById("videoFile");
        const file = fileInput.files[0];
        const messagesDiv = $('#messages');

        if (!textInput.value.trim() && !file) {
            return;
        }

        if (isSending) return;
        isSending = true;

        if (textInput.value.length > 1000) {
            isSending = false;
            return;
        }

        const loadingId = 'loading-'+Date.now();
        const $loadingMessage = $(`
            <div id="${loadingId}" class="message-loading message-content me">
                <div class="loading-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>
        `);

        messagesDiv.append($loadingMessage);
        messagesDiv.scrollTop(messagesDiv[0].scrollHeight);

        if (file) {
            const fileName = file.name;
            if (!fileName || fileName.trim() === '' || fileName.startsWith('.')) {
                $(`#${loadingId}`).html('<span style="color:#dc3545">File name is missing or invalid.</span>').css('background', 'rgba(220, 53, 69, 0.1)');
                isSending = false;
                return;
            }
        }

        try {
            let mediaUrl = null;

            if (file) {
                const formData = new FormData();
                formData.append("video", file);

                const response = await fetch("/upload_video", { method: "POST", body: formData });
                const data = await response.json();

                if (data.success && data.url) {
                    mediaUrl = data.url;
                    $("#videoFile").val("");
                    $("#mediaPreview").empty();
                } else {
                    throw new Error(data.error || 'Upload failed');
                }
            }

            const messageHandler = function() {
                $('#'+loadingId).remove();
                socket.off('new_message', messageHandler);
                isSending = false;
            };
            socket.on('new_message', messageHandler);

            // Include reply information in the message
            socket.emit('send_message', {
                text: textInput.value.trim(),
                nickname: currentUsername,
                media_url: mediaUrl,
                timestamp: Date.now(),
                reply_to: currentReplyMessageId,  // Add this field
                reply_text: currentReplyText    // Add this field
            });

            textInput.value = "";
            resetAndAdjustHeight($userInput, minHeight);
            
            // Clear reply state after sending
            $('#replyPreview').remove();
            currentReplyMessageId = null;
            currentReplyText = '';

        } catch (error) {
            console.error("Send error:", error.message || error);
            $(`#${loadingId}`).html('<span style="color:#dc3545">Failed to send</span>')
                           .css('background', 'rgba(220, 53, 69, 0.1)');
            setTimeout(() => {
                $(`#${loadingId}`).fadeOut(300, function() {$(this).remove()});
            }, 5000);
            isSending = false;
        }
    }

    // Modify the addMessage function to handle replies
    function addMessage(msg) {
        const $messagesDiv = $('#messages');
        let mediaHTML = "";
        if (msg.media_url) {
            // ... existing media handling code ...
        }

        const isMe = (msg.nickname === currentUsername);
        const time = new Date(msg.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        let editedTextHTML = `<span class="edited-text">${msg.edited ? 'Edited' : ''}</span>`;

        let replyHTML = '';
        if (msg.reply_to && msg.reply_text) {
            replyHTML = `
                <div class="reply-preview">
                    <div class="reply-line"></div>
                    <div class="reply-content">
                        <span class="reply-username">${escapeHtml(msg.nickname)}</span>
                        <span class="reply-text">${formatMessageText(msg.reply_text)}</span>
                    </div>
                </div>
            `;
        }

        $messageContainer = $('<div>')
            .addClass(isMe ? 'me' : '')
            .addClass('message-content')
            .attr('data-message-id', msg.id)
            .html(`
                <img src="${msg.profile_pic || '/static/default_profile.png'}" class="message-profile-pic">
                <div class="message-body">
                    <div class="message-header">
                        <span class="message-username">${escapeHtml(msg.nickname)}</span>
                        <span class="timestamp-inline">${time}</span>
                    </div>
                    ${replyHTML}
                    <div class="message-text">${parseLinks(formatMessageText(msg.text))}</div>
                    ${mediaHTML}
                    ${editedTextHTML}
                </div>
            `);

        $messagesDiv.append($messageContainer);
        $messagesDiv.scrollTop($messagesDiv[0].scrollHeight);
    }
</script>