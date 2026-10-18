var labels = {
    waiting: 'Preparing the dock…',
    loading: 'Loading the dock…',
    active: 'Dock startup is active.',
    disabled: 'Dock startup is disabled.',
    blocked: 'The original menu is available. The dock needs a compatibility check.',
    failed: 'The dock could not load. The original menu is available.'
};
try {
    tizen.application.launch(
        'tizendock0.svc',
        function () {},
        function () {}
    );
} catch (e) {}
function update() {
    var r = new XMLHttpRequest();
    r.open('GET', 'http://127.0.0.1:8098/status');
    r.setRequestHeader('X-Tizen-Dock-Status', '__STATUS_KEY__');
    r.timeout = 1500;
    r.onload = function () {
        try {
            document.getElementById('state').textContent =
                labels[JSON.parse(r.responseText).state] || 'Checking startup…';
        } catch (e) {}
    };
    r.send();
}
setInterval(update, 2000);
update();
document.addEventListener('keydown', function (e) {
    if (e.keyCode === 10009) {
        try {
            tizen.application.getCurrentApplication().exit();
        } catch (e) {}
    }
});
