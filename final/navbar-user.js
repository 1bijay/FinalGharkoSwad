/* Show logged-in user name in navbar (stored in localStorage) */
(function () {
    var name = localStorage.getItem('gharKoSwad_userName');
    var el = document.getElementById('navbarUsername');
    if (el) el.textContent = (name && name.trim()) ? name.trim() : 'User';
})();
