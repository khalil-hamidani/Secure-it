const body = document.querySelector("body");
const lis = document.getElementsByClassName("11");

switch (body.id) {
  case "":
    for (const li of lis) {
      li.classList.remove("active")
    }
    lis[0].classList.add("active")
    break;
    case "Encryption":
      for (const li of lis) {
        li.classList.remove("active")
      }
      lis[1].classList.add("active")
      break;
      case "Decryption":
      for (const li of lis) {
        li.classList.remove("active")
      }
      lis[2].classList.add("active")
      break;
      case "passwordsGen":
      for (const li of lis) {
        li.classList.remove("active")
      }
      lis[3].classList.add("active")
      break;
      case "passman":
      for (const li of lis) {
        li.classList.remove("active")
      }
      lis[4].classList.add("active")
      break;
  default:
    break;
}