function Get-F03CanonicalTextBytes {
    param([Parameter(Mandatory)][string]$Path)

    $content = [IO.File]::ReadAllBytes($Path)
    $output = [IO.MemoryStream]::new()
    try {
        $lineStart = 0
        for ($index = 0; $index -lt $content.Length; $index++) {
            if ($content[$index] -ne 10) { continue }
            $lineEnd = $index
            if ($lineEnd -gt $lineStart -and $content[$lineEnd - 1] -eq 13) { $lineEnd-- }
            while ($lineEnd -gt $lineStart -and $content[$lineEnd - 1] -in @(9, 32)) { $lineEnd-- }
            $output.Write($content, $lineStart, $lineEnd - $lineStart)
            $output.WriteByte(10)
            $lineStart = $index + 1
        }
        if ($lineStart -lt $content.Length) {
            $lineEnd = $content.Length
            while ($lineEnd -gt $lineStart -and $content[$lineEnd - 1] -in @(9, 32)) { $lineEnd-- }
            $output.Write($content, $lineStart, $lineEnd - $lineStart)
        }
        return $output.ToArray()
    }
    finally {
        $output.Dispose()
    }
}

function Get-F03Sha256 {
    param([Parameter(Mandatory)][byte[]]$Content)

    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash($Content))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }
}

function Get-F03CanonicalTextHash {
    param([Parameter(Mandatory)][string]$Path)
    return Get-F03Sha256 (Get-F03CanonicalTextBytes $Path)
}

function Get-F03GitStatus {
    param([Parameter(Mandatory)][string]$RepoRoot)

    $status = @(& git -C $RepoRoot -c core.quotepath=false status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) { throw 'F03_GIT_STATUS_UNAVAILABLE' }
    return $status
}

function Assert-F03CleanStatus {
    param([string[]]$Status = @())
    if (@($Status).Count -gt 0) {
        throw "F03_PRE_RUN_WORKTREE_NOT_CLEAN: $($Status -join '; ')"
    }
}

function Get-F03ImplementationTreeHash {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string[]]$RelativePaths
    )

    $arguments = @('-C', $RepoRoot, 'ls-tree', '-r', '--full-tree', 'HEAD', '--') + $RelativePaths
    $entries = @(& git @arguments)
    if ($LASTEXITCODE -ne 0 -or $entries.Count -eq 0) { throw 'F03_IMPLEMENTATION_TREE_UNAVAILABLE' }
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($entries -join "`n") + "`n")
    return Get-F03Sha256 $bytes
}

Export-ModuleMember -Function Get-F03CanonicalTextHash, Get-F03GitStatus, Assert-F03CleanStatus, Get-F03ImplementationTreeHash
