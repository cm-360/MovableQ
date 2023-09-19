import { getCookie, setCookie } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

    // ########## Method Selection ##########

    // method selection form
    const methodForm = document.getElementById("methodForm");
    // method info cards
    const methodCardGroup = document.getElementById("methodCardGroup");
    const methodCards = methodCardGroup.getElementsByClassName("card");
    // wrapper buttons
    const methodButtonFc = document.getElementById("methodButtonFc");
    const methodButtonMii = document.getElementById("methodButtonMii");

    function selectMethod() {

    }

    function updateMethodSelection(selectedCard, radioButton) {
        for (let card of methodCards) {
            if (selectedCard == card) {
                card.classList.remove("border-secondary-subtle");
                card.classList.add("border-primary");
            } else {
                card.classList.add("border-secondary-subtle");
                card.classList.remove("border-primary");
            }
        }
    }

    for (let card of methodCards) {
        const button = card.getElementByClassName("btn-check");
        card.addEventListener("click", event => updateMethodSelection(card));
    }

    // ##########  ##########

})();