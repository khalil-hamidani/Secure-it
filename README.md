# **Secue iT**

- CS50 final project by [HavardX](https://pll.harvard.edu/course/cs50-introduction-computer-science?delta=0)
- You can find my Video Demo [here 🔗](https://www.youtube.com)
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

|                         Login                         |
| :---------------------------------------------------: |
| <img src="/static/img/screen1.png" width="800"> |

- Login and Register page

|                         Login                         |                       register                        |
| :---------------------------------------------------: | :---------------------------------------------------: |
| <img src="/static/img/screen2.png" width="400"> | <img src="/static/img/screenshots/screen3.png" width="400"> |

- Homepage and Responsive show case

|                      Encryption                       |                         Result                          |
| :---------------------------------------------------: | :-----------------------------------------------------: |
| <img src="/static/img/screenshots/screen4.png" width="400"> | <img src="/static/img/screenshots/screen5.png" width = "400"> |

|                      Decryption                       |                         Result                          |
| :---------------------------------------------------: | :-----------------------------------------------------: |
| <img src="/static/img/screenshots/screen6.png" width="400"> | <img src="/static/img/screenshots/screen7.png" width = "400"> |

## About CS50

CS50 is a openware course from Havard University and taught by David J. Malan

Introduction to the intellectual enterprises of computer science and the art of programming. This course teaches students how to think algorithmically and solve problems efficiently. Topics include abstraction, algorithms, data structures, encapsulation, resource management, security, and software engineering. Languages include C, Python, and SQL plus students’ choice of: HTML, CSS, and JavaScript (for web development).

Thank you for all CS50.

Where I get CS50 course? [https://cs50.harvard.edu/x/2022/](https://cs50.harvard.edu/x/2022/)
