#ifndef _GRAPH_BUILDER_H
#define _GRAPH_BUILDER_H

#include <any>
#include <memory>

#include "_builder/expression.hpp"
#include "_builder/event.hpp"

namespace builder::internals::builders
{
    Expression<Event> orGraphBuilder(std::any definition);
}

#endif // _GRAPH_BUILDER_H
