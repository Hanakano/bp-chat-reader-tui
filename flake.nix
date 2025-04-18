{
  description = "A Nix-flake-based Python development environment";
  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.*.tar.gz";
  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        pkgs = import nixpkgs { inherit system; };
      });
    in
    {
      devShells = forEachSupportedSystem ({ pkgs }: {
        default = pkgs.mkShell {
          venvDir = ".venv";
          packages = with pkgs; [
            python312
            python312Packages.tqdm
            python312Packages.pip
            python312Packages.pyperclip
            python312Packages.venvShellHook
            uv
          ];
          shellHook = ''
            echo "Initializing env..."
            echo "🔁 Loading environment variables from .env..."
            if [ -f .env ]; then
              export $(grep -v '^#' .env | xargs)
            else
              echo "⚠️  .env file not found. You may want to copy .env.sample and fill it in."
            fi
          '';
        };
      });
    };
}
