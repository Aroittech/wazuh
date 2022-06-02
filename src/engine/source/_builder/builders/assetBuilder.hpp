#ifndef _ASSET_BUILDER_H
#define _ASSET_BUILDER_H

#include <any>

#include "_builder/expression.hpp"

namespace builder::internals::builders
{
    Expression assetBuilder(std::any definition);
}

#endif // _ASSET_BUILDER_H
