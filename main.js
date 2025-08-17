navigator.geolocation.getCurrentPosition(
  function(position) {
    // success
    fetch('/location', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      })
    })
    .then(response => {
      if (response.ok) {
        document.getElementById("status").textContent = "Location sent!";
      } else {
        document.getElementById("status").textContent = "Failed to send location.";
      }
    })
    .catch(() => {
      document.getElementById("status").textContent = "Network error sending location.";
    });
  },
  function(error) {
    document.getElementById("status").textContent = "Error: " + error.message;
  }
);
