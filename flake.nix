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
            python312Packages.venvShellHook
            uv
          ];
          
          shellHook = ''
            echo "Initializing env..."
            # uv install
          '';
          
          # Set environment variables within the shell
          BOTPRESS_WORKSPACE_ID = "wkspace_01JAEPF5382463QW7FKWSGFHJA";
          BOTPRESS_BOT_ID = "de90d852-0739-4f36-bad6-a5cb5f9df49c";
          BOTPRESS_TOKEN = "bp_pat_0lF5ffsJGmkQuRha92zExVggmnuyflpS9KGT";
        };
      });
    };
}
