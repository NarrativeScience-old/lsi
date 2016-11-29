{
  pkgs ? import <nixpkgs> {},
  # For setting python version. Ignored if `pythonPackages` argument
  # is explicitly given.
  python3 ? true,
  pythonPackages ? if python3 then pkgs.python3Packages
                   else pkgs.python2Packages,
}:

let
  inherit (pythonPackages) buildPythonPackage;
  colored = buildPythonPackage rec {
    name = "colored-${version}";
    version = "1.1.5";
    doCheck = false;
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/source/c/colored/${name}.tar.gz";
      sha256 = "1r1vsypk8v7az82d66bidbxlndx1h7xd4m43hpg1a6hsjr30wrm3";
    };
  };
in


buildPythonPackage rec {
  name = "lsi-${version}";
  version = "0.3.1";
  propagatedBuildInputs = [
    colored
    pkgs.openssh
    pkgs.which
    pythonPackages.boto
  ];
  src = ./.;
  # Silly check phase for now, better than nothing until we write real tests...
  checkPhase = ''
    $out/bin/lsi --help >/dev/null
  '';
}
