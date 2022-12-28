function showpassword(id) {
    var input = document.getElementById(id);
    var icon = document.getElementById("passwordIcon");
    if (input.type === "password") {
      input.type = "text";
      icon.classList.remove("ri-lock-unlock-fill")
      icon.classList.add("ri-lock-2-fill")
    } else {
      input.type = "password";
      icon.classList.remove("ri-lock-2-fill")
      icon.classList.add("ri-lock-unlock-fill")
      
    }
  }