//
// Created by khalidzhang on 2023/9/18.
//
#include "book_actor.h"
#include "doctest.h"
#include "std_log.h"

using namespace generated_test::nn;

TEST_CASE("simple_test") {
  BookActor bookActor{};
  bookActor.set_name_("book1");
  LOG_DEBUG("book name is " << bookActor.get_name_())
}