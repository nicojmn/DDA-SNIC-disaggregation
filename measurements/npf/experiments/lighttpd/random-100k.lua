math.randomseed(os.time())

request = function()
    local path = "/100k_" .. math.random(1, 50000) .. ".bin"
    return wrk.format(nil, path)
end
