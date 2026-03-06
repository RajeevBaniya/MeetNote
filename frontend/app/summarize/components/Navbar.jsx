"use client";

function Navbar() {
  return (
    <nav className="navbar-main">
      <div className="navbar-wrapper">
        <div className="flex justify-between items-center">
          <a href="/" className="navbar-brand">
            <span className="brand-badge" aria-hidden="true">
              S
            </span>
            <span className="brand-text">
              Summer<span className="brand-accent">Ease</span>
            </span>
          </a>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
