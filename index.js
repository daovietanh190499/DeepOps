function init() {
    const sliders = document.getElementsByClassName("tick-slider-input");

    for (let slider of sliders) {
        slider.oninput = onSliderInput;
        updateProgress(slider);
        setTicks(slider);
        setLabels(slider);
    }
}

function onSliderInput(event) {
    updateProgress(event.target);
    setTicks(event.target);
}

function updateProgress(slider) {
    let progress = document.getElementById(slider.dataset.progressId);
    const percent = getSliderPercent(slider);

    progress.style.width = percent * 100 + "%";
}

function getSliderPercent(slider) {
    const range = slider.max - slider.min;
    const absValue = slider.value - slider.min;

    return absValue / range;
}

function setTicks(slider) {
    const percent = getSliderPercent(slider);
    let container = document.getElementById(slider.dataset.tickId);
    container.innerHTML = ""
    const spacing = parseFloat(slider.dataset.tickStep);
    const sliderRange = slider.max - slider.min;
    const tickCount = sliderRange / spacing + 1;

    for (let ii = 0; ii < tickCount; ii++) {
        let tick = document.createElement("span");

        if (ii/tickCount > percent) {
            tick.className = "tick-slider-tick-gray";
        } else {
            tick.className = "tick-slider-tick";
        }

        container.appendChild(tick);
    }
}

function setLabels(slider) {
    const percent = getSliderPercent(slider);
    let container = document.getElementById(slider.dataset.labelId);
    let listLabel = slider.dataset.labels.split(',');
    container.innerHTML = ""
    const spacing = parseFloat(slider.dataset.tickStep);
    const sliderRange = slider.max - slider.min;
    const tickCount = sliderRange / spacing + 1;

    for (let ii = 1; ii < tickCount; ii++) {
        let tick = document.createElement("span");
        tick.className = "label-slider-label";
        tick.style = "width:" + 100/(tickCount-1) + "%";
        tick.innerText = listLabel[ii-1];
        container.appendChild(tick);
    }
}

window.onload = init;