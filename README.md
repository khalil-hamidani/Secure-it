# **Secue iT**

- CS50 final project by [HavardX](https://pll.harvard.edu/course/cs50-introduction-computer-science?delta=0)
- You can find my Video Demo [here 🔗](https://youtu.be/QauGfL4t2Fs)
  ![Logo](/static/img/widelogo.png)

## Description

Secure it is a cybersecurity web application that provides several features to help users protect their online accounts and data.

One of the main features of Secure it is the ability to **Encrypt** and **Decrypt** messages using the [Caesar cipher](https://en.wikipedia.org/wiki/Caesar_cipher). This allows users to send encrypted messages to each other, which can only be decrypted by someone who knows the correct shift value.

Secure It also includes a **Password Generator**, which can be used to create strong, random passwords for online accounts. Users can specify the length and complexity of the password, and the generator will generate a secure password that meets these requirements.

In addition to the password generator, Secure It also includes a **Password Manager** feature. This allows users to store their login credentials for different online accounts in a secure location.

Overall, Secure It is a useful tool for users who want to protect their online accounts and data by using strong passwords and encrypted communication.

## Tools

- **HTML** : used to define the structure and layout of a web page, including the text, images, and other media that it contains.
- **CSS** : used to control the appearance of elements on a web page, including the colors, fonts, layout, and other visual properties.
- **JavaScript** : used to build interactive elements on web pages and the main function of the web application.
- **Python** :(**Flask framework**) used as the backend for web applications, meaning that it runs on a server and handles the server-side logic and processing for the app.
- **SQL** : used as a database management system for the application.

## Implementation

The app is structured using HTML elements to define the layout and content of the various pages , there are 11 html Files stored in the templates folder for the whole project: `index.html` for the landing page , `login.html` and `register.html` for login and register forms and `encryption.html`, `decryption.html`, `passwordGen.html`, `passwordMan.html` for the main features of the the app. `user.html`, `bad.html` for showing the user account and error messages, and finally the `template.html` is the file where all the previous files are extended from it using the **jinja2** syntax

CSS is used to style the app, including the layout, fonts, colors, and other visual elements all inside `styles.css` file in the static folder.

JavaScript is used to implement the core functionality of the app, including the Caesar cipher encryption and decryption algorithms in the `encryption.js` and `decryption.js` files one the static folder, the password generator, and the password manager in the `passGen.js` and `passMan.js`.

Data is stored and retrieved from a backend server with database using Flask: `app.py` is the main python script that allwos users to sign in , log in and store there passwords inside the datatbase stored in `secure.db`

## Pictures

|                    Main page                    |
| :---------------------------------------------: |
| <img src="/static/img/screen1.png" width="800"> |

- Login and Register page

|                      Login                      |                    register                     |
| :---------------------------------------------: | :---------------------------------------------: |
| <img src="/static/img/screen2.png" width="400"> | <img src="/static/img/screen3.png" width="400"> |

- Encryption and Decryption show case

|                   Encryption                    |                      Result                       |
| :---------------------------------------------: | :-----------------------------------------------: |
| <img src="/static/img/screen4.png" width="400"> | <img src="/static/img/screen5.png" width = "400"> |

|                   Decryption                    |                      Result                       |
| :---------------------------------------------: | :-----------------------------------------------: |
| <img src="/static/img/screen6.png" width="400"> | <img src="/static/img/screen7.png" width = "400"> |

- password Generator an password manager show case

|               Password Generator                |                      Result                       |
| :---------------------------------------------: | :-----------------------------------------------: |
| <img src="/static/img/screen8.png" width="400"> | <img src="/static/img/screen9.png" width = "400"> |

|                 Password Manager                 |                       Result                       |
| :----------------------------------------------: | :------------------------------------------------: |
| <img src="/static/img/screen10.png" width="400"> | <img src="/static/img/screen11.png" width = "400"> |

## Algorithms

### Encryption

```javascript
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
```

this function takes a plain text string and a shift value , and returns an encrypted string.

To encrypt the plain text, the function first converts it to lower case and then loops through each character in the plain text. For each character, it checks if it is a letter or not by checking if it exists in the alphabet string. If it is not a letter, it is simply added to the encrypted text. If it is a letter, the function calculates the new index of the letter in the alphabet using the shift value, and then adds the corresponding letter at that index to the encrypted text.

Here is an example of how you can run this function:

```javaScript

const plainText = "Hello, World!";
const shift = 3;
const encryptedText = encryptCaesarCipher(plainText, shift);

console.log(encryptedText); // Output: "khoor, zruog!"
```

### Decryption

```javaScript
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
```

This function takes an encrypted string and a shift value, and returns the corresponding decrypted string.

To decrypt the encrypted text, the function first converts it to lower case and then loops through each character in the encrypted text. For each character, it checks if it is a letter or not by checking if it exists in the alphabet string. If it is not a letter, it is simply added to the decrypted text. If it is a letter, the function calculates the original index of the letter in the alphabet using the shift value, and then adds the corresponding letter at that index to the decrypted text.

Here is an example of how you can run this function:

```javascript
const encryptedText = "khoor, zruog!";
const shift = 3;
const decryptedText = decryptCaesarCipher(encryptedText, shift);

console.log(decryptedText); // Output: "hello, world!"
```

### Password Generator

```javascript
function generatePassword(lower, upper, number, symbol, length) {
  let generatedPassword = "";
  const typesCount = lower + upper + number + symbol;
  const typesArr = [{ lower }, { upper }, { number }, { symbol }].filter((item) => Object.values(item)[0]);

  if (typesCount === 0) {
    return "";
  }

  for (let i = 0; i < length; i += typesCount) {
    typesArr.forEach((type) => {
      const funcName = Object.keys(type)[0];
      generatedPassword += randomFunc[funcName]();
    });
  }
```

This is a function that generates a random password of a specified length by including a combination of lowercase letters, uppercase letters, numbers, and symbols.

The function takes in four boolean arguments: lower, upper, number, and symbol, which specify whether to include lowercase letters, uppercase letters, numbers, and symbols in the generated password, respectively. It also takes in a length argument, which specifies the length of the generated password.

The function first initializes an empty string called generatedPassword, which will be used to store the generated password. It then calculates the number of types of characters that will be included in the password by adding up the values of the lower, upper, number, and symbol arguments. If this count is zero, the function returns an empty string.

The function then creates an array called typesArr that includes objects representing each type of character to be included in the password, based on the values of the lower, upper, number, and symbol arguments. It then filters this array to only include objects whose values are true.

Finally, the function enters a loop that runs for as many iterations as the length of the password. On each iteration, it calls the appropriate function from an object called randomFunc to generate a random character of each type specified in the typesArr array, and appends these characters to the generatedPassword string.

Here is an example of how you can run this function:

```javascript
const lower = true;
const upper = true;
const number = true;
const symbol = false;
const length = 20;
const password = generatePassword(lower, upper, number, symbol, length);

console.log(password); // Output: a random password of length 20 that includes lowercase letters, uppercase letters, and numbers
```

### Password Manager

```python
@app.route("/passwordMan",methods=["GET", "POST"])
@login_required
def passwordMan():
    user = "Account"
    if session.get("user_id"):
        user = db.execute("SELECT name FROM users WHERE id = ?",session["user_id"])[0]
    if request.method == "GET":
        accounts = db.execute("SELECT * FROM passwords WHERE user_id = ?",session["user_id"])
        return render_template("passwordMan.html",nav=True,accounts=accounts,user=user)
    else:
        accountName = request.form.get("name")
        accountPassword = request.form.get("password")
        accountLink = request.form.get("link")
        if not accountName:
            return error("No account name is providedd !")
        elif not accountPassword:
            return error("No account Password is providedd !")
        elif not accountLink:
            return error("No account Link is providedd !")
        db.execute("INSERT INTO passwords (user_id,name,link,password) VALUES (?,?,?,?);",session["user_id"],accountName,
          accountLink,accountPassword)
        return redirect("/passwordMan")
```

This is a route handler function for the web application that allows users to manage their passwords. It is written in Python and uses the Flask web framework.

The function is decorated with @app.route and @login_required, which means that it will be executed whenever a user accesses the "/passwordMan" URL and is logged in.

The function first retrieves the name of the logged-in user from the database. If the request method is "GET", the function retrieves all the passwords belonging to the logged-in user from the database and renders a template called "passwordMan.html" with the retrieved passwords and the user's name.

If the request method is "POST", the function gets the values of the "name", "password", and "link" form fields and checks if they are all present. If any of them is missing, the function returns an error message. Otherwise, it inserts the values into the "passwords" table in the database and redirects the user back to the "/passwordMan" URL.

## Running

To run and test the Application on your localhost, execute this command on your terminal after forking the repository

```bash
  ./comands.bash
```

OR

```bash
  python3 app.py
```

Wich will run the flask app on `http://127.0.0.1:5000`

## Course description

This is CS50x , Harvard University's introduction to the intellectual enterprises of computer science and the art of programming for majors and non-majors alike, with or without prior programming experience. An entry-level course taught by David J. Malan, CS50x teaches students how to think algorithmically and solve problems efficiently. Topics include abstraction, algorithms, data structures, encapsulation, resource management, security, software engineering, and web development. Languages include C, Python, SQL, and JavaScript plus CSS and HTML. Problem sets inspired by real-world domains of biology, cryptography, finance, forensics, and gaming. The on-campus version of CS50x , CS50, is Harvard's largest course.

Thank you for all CS50.

Where I get CS50 course? [https://cs50.harvard.edu/x/2022/](https://cs50.harvard.edu/x/2022/)
