import { getCookie, setCookie } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

    // method selection form
    const methodForm = document.getElementById("methodForm");
    const methodRadioFc = document.getElementById("methodRadioFc");
    const methodRadioMii = document.getElementById("methodRadioMii");
    const methodRadioFcLabel = document.getElementById("methodRadioFcLabel");
    const methodRadioMiiLabel = document.getElementById("methodRadioMiiLabel");

    function updateMethodRadio() {
        methodRadioFcLabel.classList.remove("border-secondary-subtle", "border-primary");
        methodRadioMiiLabel.classList.remove("border-secondary-subtle", "border-primary");
        if (methodRadioFc.checked) {
            methodRadioFcLabel.classList.add("border-primary");
        } else if (methodRadioMii.checked) {
            methodRadioMiiLabel.classList.add("border-primary");
        }
    }
    
    updateMethodRadio();
    methodRadioFcLabel.addEventListener("click", updateMethodRadio);
    methodRadioMiiLabel.addEventListener("click", updateMethodRadio);

})();