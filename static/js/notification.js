document.addEventListener("DOMContentLoaded", function() {
  if (window.Notification && Notification.permission !== "granted") {
	Notification.requestPermission();
  }
});

function showDesktopNotification(sender, message) {
	if (Notification.permission === "granted" && sender !== currentUsername) {
		const notification = new Notification(`New message from ${sender}`, {
			body: message.length > 100 ? message.substring(0, 100) + '...' : message,
			icon: '/static/notification-icon.png',
			badge: '/static/badge-icon.png',
			vibrate: [100, 50, 100],
			requireInteraction: false,
			silent: false 
	});

	notification.onclick = function() {
		window.focus();
		this.close();
	};

		setTimeout(() => notification.close(), 8000);
	}
}