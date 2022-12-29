const encrypt = document.querySelector("#generate"); // Encrypt Text 🛠️
const input = document.querySelector(".Encryption-container");
const output = document.querySelector(".Encryption-output-container");

const back = document.querySelector("#back"); // back to Encryption 🛠️
const encrypted = document.querySelector("#cipher");

let copy = document.querySelector("#copy"); //Copy Ciphered Text 📝

encrypt.addEventListener("click", () => {
  let plainText = document.querySelector("#plaintxt").value;
  let key = +document.querySelector("input").value;
  if (plainText != "" && key <= 26 && key >= 1) {
    input.classList.add("disabled");
    output.classList.remove("disabled");
    encrypted.value = encryptCaesarCipher(plainText, key);
    document.querySelector("#plaintxt").value = "";
  } else {
    if (plainText === "") {
      encrypt.innerText = "⚠️ Please Enter your PlainText First ⚠️";
      setTimeout(function () {
        encrypt.innerText = "Encrypt Text 🛠️";
      }, 2000);
    } else {
      encrypt.innerText = "⚠️ Please Enter a valid key ⚠️";
      setTimeout(function () {
        encrypt.innerText = "Encrypt Text 🛠️";
      }, 2000);
    }
  }
});

back.addEventListener("click", () => {
  output.classList.add("disabled");
  input.classList.remove("disabled");
});

copy.addEventListener("click", () => {
  navigator.clipboard.writeText(encrypted.value).then(() => {
    copy.innerText = "✅ Copied";
    setTimeout(function () {
      copy.innerText = "Copy Ciphered Text 📝";
    }, 1000);
  });
});

function encryptCaesarCipher(plainText, shift) {
  const alphabet = "abcdefghijklmnopqrstuvwxyz";
  const plainTextLowerCase = plainText.toLowerCase();
  let encryptedText = "";

  for (let i = 0; i < plainTextLowerCase.length; i++) {
    const currentChar = plainTextLowerCase[i];
    const currentIndex = alphabet.indexOf(currentChar);

    if (currentIndex === -1) {
      encryptedText += currentChar;
    } else {
      const newIndex = (currentIndex + shift) % 26;
      const newChar = alphabet[newIndex];
      encryptedText += newChar;
    }
  }

  return encryptedText;
}