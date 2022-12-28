const encrypt = document.querySelector("#generate");
const input = document.querySelector(".Encryption-container");
const output = document.querySelector(".Encryption-output-container");

const back = document.querySelector("#back");
const encrypted = document.querySelector("#cipher");

let copy = document.querySelector("#copy");

encrypt.addEventListener("click", () => {
  let plainText = document.querySelector("#plaintxt").value;
  let key = +document.querySelector("input").value;
  if (plainText != "" && key <= 26 && key >= 1) {
    input.classList.add("disabled");
    output.classList.remove("disabled");
    encrypted.value = decryptCaesarCipher(plainText, key);
    document.querySelector("#plaintxt").value = "";
  } else {
    if (plainText === "") {
      encrypt.innerText = "⚠️ Please Enter your CipherText First ⚠️";
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
      copy.innerText = "Copy CipherText 📝";
    }, 1000);
  });
});

function decryptCaesarCipher(encryptedText, shift) {
  const alphabet = "abcdefghijklmnopqrstuvwxyz";
  const encryptedTextLowerCase = encryptedText.toLowerCase();
  let decryptedText = "";

  for (let i = 0; i < encryptedTextLowerCase.length; i++) {
    const currentChar = encryptedTextLowerCase[i];
    const currentIndex = alphabet.indexOf(currentChar);

    if (currentIndex === -1) {
      decryptedText += currentChar;
    } else {
      const newIndex = (currentIndex - shift + 26) % 26;
      const newChar = alphabet[newIndex];
      decryptedText += newChar;
    }
  }

  return decryptedText;
}
