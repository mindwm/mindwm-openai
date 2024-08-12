{ lib
, pkgs
, my_python
}:
with pkgs;

python3.pkgs.buildPythonApplication {
  pname = "mindwm-knfunc";
  version = "0.1.0";

  src = ./.;

  propagatedBuildInputs = [ my_python ];
  dependencies = [
    my_python
  ];

  pythonImportsCheck = [
    "knfunc"
  ];
  format = "pyproject";
  nativeBuildInputs = with python3.pkgs; [ setuptools ];
}
