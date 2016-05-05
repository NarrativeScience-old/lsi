{
  pkgsPath ? <nixpkgs>,
  # For future; not supported yet due to upstream deps ;(
  python3 ? false
}:

let
  pkgs = import pkgsPath {};
  pythonPackages = if python3 then pkgs.python3Packages
                              else pkgs.python2Packages;
  inherit (pythonPackages) buildPythonPackage;
  colored = buildPythonPackage rec {
    name = "colored-${version}";
    version = "1.1.5";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/source/c/colored/${name}.tar.gz";
      md5 = "dddb7dea666de595119764dbb611a0e7";
    };
  };
in


buildPythonPackage rec {
  name = "lsi-${version}";
  version = "0.2.1";
  propagatedBuildInputs = [
    colored
    pkgs.openssh
    pkgs.which
    pythonPackages.boto
    pythonPackages.ipython
  ];
  src = ./.;
}
