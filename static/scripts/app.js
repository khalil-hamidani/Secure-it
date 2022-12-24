const counters = document.querySelectorAll(".counter");
counters.forEach((counter) => {
  counter.innerText = "0";
  const updateCounter = () => {
    const target = +counter.getAttribute("data-target");
    const c = +counter.innerText;
    const increment = target / 150;
    if (c < target) {
      counter.innerText = `${Math.ceil(c + increment)}`;
      setTimeout(updateCounter, 1);
    } else {
      counter.innerText = target;
    }
  };
  updateCounter();
});

const left = document.querySelector(".left");
const right = document.querySelector(".right");
const compareContainer = document.querySelector(".compareContainer");
left.addEventListener("mouseenter", () => {
  compareContainer.classList.add("hover-left");
});
left.addEventListener("mouseleave", () => {
  compareContainer.classList.remove("hover-left");
});

right.addEventListener("mouseenter", () => {
  compareContainer.classList.add("hover-right");
});
right.addEventListener("mouseleave", () => {
  compareContainer.classList.remove("hover-right");
});


$("yes").on("mousedown", function(){
  timeout = setInterval(function(){
          var cs = $("body").scrollTop();
          $("body").scrollTop(cs+1)
  }, 10);  // <--- Change this value to speed up/slow down scrolling

  return false;
});
$("yes").on("mouseup", function(){
  clearInterval(timeout);
  return false;
});