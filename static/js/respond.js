let shiftHeld = false;
let isHovering = false;
let hoveredMessage = null;

let notificationSoundEnabled = true;
notificationSound = new Audio('./static/sounds/test.wav');
notificationSound.preload = 'auto';

$(document).on('keydown keyup', function(e) {
    shiftHeld = e.shiftKey;

    if (hoveredMessage) {
        hoveredMessage.find('.openReply').css('display', shiftHeld ? 'block' : 'none');
    }

    if (isHovering) {
        $('#replyPreview').css('cursor', shiftHeld ? 'pointer' : 'default');
    }
});

$(document).on('mouseenter', '.message-content', function() {
    if (!$(this).hasClass('me')) {
        hoveredMessage = $(this);
        $(this).find('.openReply').css('display', shiftHeld ? 'block' : 'none');
    }
}).on('mouseleave', '.message-content', function() {
    $(this).find('.openReply').css('display', 'none');
    hoveredMessage = null;
});

$('#chatContainer').on('mouseenter', '#replyPreview', function() {
    isHovering = true;
    $(this).css('cursor', shiftHeld ? 'pointer' : 'default');
}).on('mouseleave', '#replyPreview', function() {
    isHovering = false;
    $(this).css('cursor', 'default');
});

$('#chatContainer').on('click', '#replyPreview', function(e) {
    if (e.shiftKey) {
        e.preventDefault();
        $(this).remove();
    }
});

$(document).ready(function() {
    const darkMode = localStorage.getItem('darkMode') === 'true';
    const soundPref = localStorage.getItem('notificationSound');

    // Dark Mode
    if (darkMode) {
        enableDarkMode();
        $('#darkModeToggle').prop('checked', true);
    }

    $('#darkModeToggle').change(function() {
        if ($(this).is(':checked')) {
            enableDarkMode();
        } else {
            disableDarkMode();
        }
    });


    // Notification Sound
    if (soundPref === 'false') {
        notificationSoundEnabled = false;
        $('#soundToggle').prop('checked', false);
    } else {
        notificationSoundEnabled = true;
        $('#soundToggle').prop('checked', true);
    }

    $('#soundToggle').change(function() {
        notificationSoundEnabled = $(this).is(':checked');
        localStorage.setItem('notificationSound', notificationSoundEnabled);
    });
});

function enableDarkMode() {
    $('body').css({
        'background-color': 'rgb(28, 28, 28)'
    });

    $('#messages').css({
        'background': 'rgb(255, 255, 255, 0.1)'
    });

    $('#userInput').css({
        'background': 'rgb(255, 255, 255, 0.1)',
        'color': 'white'
    });

    $('.test').css({
        'background': 'rgb(51, 51, 51)',
        'color': 'white'
    })

    localStorage.setItem('darkMode', 'true');
}

function disableDarkMode() {
    $('body, #messages, #userInput, .test').removeAttr('style');
    localStorage.setItem('darkMode', 'false');
}