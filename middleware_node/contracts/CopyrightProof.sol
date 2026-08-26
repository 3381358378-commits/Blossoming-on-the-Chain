// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CopyrightProof {
    struct Copyright {
        string workHash;
        string creator;
        uint256 timestamp;
    }
    mapping(string => Copyright) public copyrights;

    event CopyrightRecorded(string workHash, string creator, uint256 timestamp);

    function recordCopyright(string memory _workHash, string memory _creator) public {
        require(bytes(copyrights[_workHash].workHash).length == 0, "Copyright already exists");
        copyrights[_workHash] = Copyright(_workHash, _creator, block.timestamp);
        emit CopyrightRecorded(_workHash, _creator, block.timestamp);
    }

    function getCopyright(string memory _workHash) public view returns (string memory, string memory, uint256) {
        Copyright memory c = copyrights[_workHash];
        return (c.workHash, c.creator, c.timestamp);
    }
}