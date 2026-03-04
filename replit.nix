{ pkgs }: {
  deps = [
    # Python 3.11
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv

    # Build dependencies
    pkgs.gcc
    pkgs.gnumake
    pkgs.pkg-config

    # Database
    pkgs.postgresql
    pkgs.postgresql.lib

    # Document processing
    pkgs.poppler_utils
    pkgs.tesseract

    # System utilities
    pkgs.curl
    pkgs.wget
    pkgs.git
    pkgs.jq

    # Development tools
    pkgs.nodejs_18
    pkgs.nodejs_18.pkgs.npm
  ];

  env = {
    PGHOST = "localhost";
    PGPORT = "5432";
    PGUSER = "postgres";
    PGPASSWORD = "postgres";
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/contract_intelligence";
    PYTHONUNBUFFERED = "1";
    PYTHONPATH = "/home/runner/${builtins.baseNameOf ./.}";
  };
}
