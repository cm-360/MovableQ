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


    // ########## Mii Mining ##########

    // upload method toggle
    const miiUploadToggle = document.getElementById("miiUploadToggle");
    const miiUploadFile = document.getElementById("mii_file");
    const miiUploadUrl = document.getElementById("mii_url");

    function toggleMiiUpload() {
        if (miiUploadFile.classList.contains("show")) {
            miiUploadUrl.classList.add("show");
            miiUploadFile.classList.remove("show");
            miiUploadToggle.innerText = "Upload a file instead";
        } else {
            miiUploadFile.classList.add("show");
            miiUploadUrl.classList.remove("show");
            miiUploadToggle.innerText = "Provide a URL instead";
        }
    }

    miiUploadToggle.addEventListener("click", toggleMiiUpload);
    toggleMiiUpload();


    // ########## LFCS: Friend Exchange ##########

    // upload method toggle
    const lfcsUploadToggle = document.getElementById("lfcsUploadToggle");
    const lfcsUploadFile = document.getElementById("lfcs_file");
    const lfcsUploadUrl = document.getElementById("lfcs_url");

    function toggleLfcsUpload() {
        if (lfcsUploadFile.classList.contains("show")) {
            lfcsUploadUrl.classList.add("show");
            lfcsUploadFile.classList.remove("show");
            lfcsUploadToggle.innerText = "Upload a file instead";
        } else {
            lfcsUploadFile.classList.add("show");
            lfcsUploadUrl.classList.remove("show");
            lfcsUploadToggle.innerText = "Provide a URL instead";
        }
    }

    lfcsUploadToggle.addEventListener("click", toggleLfcsUpload);
    toggleLfcsUpload();


    // ########## LFCS: Mii  ##########



})();