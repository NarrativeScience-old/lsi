with import <nixpkgs> {};

let
  colored = buildPythonPackage rec {
    name = "colored-${version}";
    version = "1.1.5";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/c/colored/${name}.tar.gz";
      md5 = "dddb7dea666de595119764dbb611a0e7";
    };
  };
in


buildPythonPackage rec {
  name = "lsi-${version}";
  version = "0.0.2";
  propagatedBuildInputs = [colored openssh which] ++
                          (with pythonPackages; [boto ipythonLight]);
  src = ./.;
}
