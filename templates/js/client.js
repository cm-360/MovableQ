import { getCookie, setCookie } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

    let key;

    // ########## Method Selection ##########

    // method selection form
    const methodForm = document.getElementById("methodForm");
    // method info cards
    const methodCardGroup = document.getElementById("methodCardGroup");
    const methodCards = methodCardGroup.getElementsByClassName("card");
    // wrapper buttons
    const methodButtonFc = document.getElementById("methodButtonFc");
    const methodButtonMii = document.getElementById("methodButtonMii");

    function updateMethodSelection(selectedCard, radioButton) {
        for (let card of methodCards) {
            if (selectedCard == card) {
                radioButton.checked = true;
                card.classList.remove("border-secondary-subtle");
                card.classList.add("border-primary");
            } else {
                card.classList.add("border-secondary-subtle");
                card.classList.remove("border-primary");
            }
        }
    }

    for (let card of methodCards) {
        const button = card.querySelector(".btn-check");
        card.addEventListener("click", event => updateMethodSelection(card, button));
    }

    function submitMethodSelection(event) {
        event.preventDefault();
        const formData = new FormData(methodForm);
        console.log(formData);
    }

    methodForm.addEventListener("submit", event => submitMethodSelection(event));


    // ##########  ##########

})();